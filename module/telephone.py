from .base import Module, Command
import asyncio
import async_timeout
from discord.errors import Forbidden

# TODO: SERVER JEOPARDY! waiting out asyncs to allow servers to guess for an answer
# additionally: using telephone as scaffolding for multiplayer trivia


class Convo:
    def check_channels(self, chan):
        return False

    def process_message(self, state):
        pass

    def end_call(self):
        pass


class Teleconvo(Convo):
    def __init__(self, chan1, chan2, cmdhost):
        self.host = cmdhost
        self.end_a = {
            'channel': chan1,
            'guild': chan1.guild
        }

        self.end_b = {
            'channel': chan2,
            'guild': chan2.guild
        }
        self.message_status = asyncio.Event()
        asyncio.create_task(self.timeout_loop())

    async def timeout_loop(self):
        self.message_status.clear()
        try:
            async with async_timeout.timeout(30):
                await self.message_status.wait()
        except asyncio.TimeoutError:
            await self.end_call()

    def check_channels(self, chan):
        return chan.id == self.end_a['channel'].id or chan.id == self.end_b['channel'].id

    async def process_message(self, state):
        self.message_status.set()
        if state.message.author.bot:
            return
        if state.message.guild.id == self.end_a['guild'].id:
            destination = self.end_b['channel']
        elif state.message.guild.id == self.end_b['guild'].id:
            destination = self.end_a['channel']
        else:
            print("what")
            return
        msg = f"**{state.message.author.name}#{state.message.author.discriminator}** {state.message.content}"
        await destination.send(msg)
        await self.timeout_loop()

    async def end_call(self, chan):
        self.message_status.set()

        ta = asyncio.create_task(self.end_a['channel'].send("**Conversation closed.**"))
        tb = asyncio.create_task(self.end_b['channel'].send("**Conversation closed.**"))

        await asyncio.wait([ta, tb])

        self.host.calllist.pop(self.end_a['guild'].id)
        self.host.calllist.pop(self.end_b['guild'].id)
        print(self.host.calllist)


class MultiConvo(Convo):
    def __init__(self, host, message_list):
        self.host = host
        self.party_size = len(message_list)
        self.channel_list = [m.channel for m in message_list]

    def check_channels(self, chan):
        return chan in self.channel_list


class TriviaConvo(MultiConvo):
    '''Rules:
- Each question must be answered by at least 50% of participants.
- Deleted questions will be penalized based on 50% of the maximum number of respondants to a question.
  therefore it is in your best interest to answer every question.
'''

    QUESTION_COUNT = 5

    def __init__(self, host, message_list, gov):
        print(host)
        print(gov)
        super().__init__(host, message_list)
        self.msg_list = message_list
        self.trivia_history = [[] for n in range(self.party_size)]
        self.accept_messages = False
        self.gov = gov
        asyncio.create_task(self.trivia_loop())
        # implement communication in between questions? 30 second window with a bool flag to track

    async def trivia_loop(self):
        result_list = self.party_size * [0]
        for q in range(self.QUESTION_COUNT):
            task_list = []
            triv = await self.gov.fetch_trivia()
            for m in range(self.party_size):
                task_list.append(asyncio.create_task(self.gov.tdb_trivia(self.msg_list[m], triv)))
            trivia_results = await asyncio.gather(*task_list)
            task_list = []
            trivia_temp_string = f"The correct answer was {triv['correct_answer']}."
            for i in range(self.party_size):
                # in this situation, deleted messages should be treated as server-wide wrong answers.
                # they will receive a 0 / (max participants in a question), making their weight at least 20%.
                # thankfully we can detect this if trivia is set to none
                results = trivia_results[i]
                print(results)
                if results[2] is None:
                    self.trivia_history[i].append((0, -1))  # placeholder to be resolved in the future
                    task_list.append(asyncio.create_task(self.channel_list[i].send(f"The trivia message was deleted. No users were counted as correct.")))
                else:
                    correct = len(results[0])
                    q_sum = correct + len(results[1])
                    result_list[i] = max(result_list[i], q_sum)
                    self.trivia_history[i].append((correct, q_sum))
                    task_list.append(asyncio.create_task(self.channel_list[i].send(f"{trivia_temp_string}\n{correct}/{q_sum} users answered correctly!")))
            await asyncio.sleep(5)
        # game over. handle results here
        for i in range(self.party_size):
            max_users = result_list[i]
            half_users = int(max_users / 2)
            correct_sum = 0
            placeholders = 0
            submission_sum = 0
            for j in range(self.QUESTION_COUNT):
                q_correct = self.trivia_history[i][j][0]
                q_sum = self.trivia_history[i][j][1]
                if q_sum < 0:
                    placeholders += 1
                    q_sum = 0
                submission_sum += max(half_users, q_sum)
                correct_sum += q_correct
            submission_sum += (max_users * placeholders)
            ratio = 0
            if submission_sum > 0:
                ratio = 100 * correct_sum / submission_sum
            result_list[i] = TriviaData(i, ratio, max_users)
        result_list.sort(reverse=True)
        # results parsed. display to users
        # indices correspond with message list, use channel prop to send out results!
        result_string = ""
        for res in range(self.party_size):
            result_string += f"#{res + 1}: {self.msg_list[result_list[res].index].guild.name} -- {result_list[res].ratio:.2f}%\n"
            # might want to parse this elsewhere, but building several user strings is unweildy
        task_list = []
        for res in range(self.party_size):  # iterate again to send finished string
            chan = self.msg_list[result_list[res].index].channel
            task_list.append(chan.send(f"**Your server finished #{res + 1}!**\n\n" + result_string))
        await asyncio.wait(task_list)
        await asyncio.sleep(10)
        asyncio.create_task(self.end_call(None))

    async def process_message(self, state):
        if self.accept_messages:
            pass
        else:
            pass

    async def end_call(self, chan):
        task_list = []
        for chan in self.channel_list:
            task_list.append(asyncio.create_task(chan.send("**Trivia game ended.**")))

        await asyncio.wait(task_list)

        for chan in self.channel_list:
            self.host.calllist.pop(chan.guild.id)
        print(self.host.calllist)


class TriviaData:
    def __init__(self, index, ratio, users):
        self.index = index
        self.ratio = ratio
        self.user_count = users

    def __eq__(self, other):
        return self.ratio == other.ratio and self.user_count == other.user_count

    def __lt__(self, other):
        if (self.ratio == other.ratio):
            return self.user_count < other.user_count
        return self.ratio < other.ratio

    def __gt__(self, other):
        if (self.ratio == other.ratio):
            return self.user_count > other.user_count
        return self.ratio > other.ratio

    def __ge__(self, other):
        return not self.__lt__(self, other)

    def __le__(self, other):
        return not self.__gt__(self, other)

    def __ne__(self, other):
        return not self.__eq__(self, other)


class Telephone(Module):
    # TODO: segregate sfw/nsfw
    def __init__(self, host):  # TODO: host instance not necessary
        super().__init__(host)
        # potentially managing hundreds of server connections at a time -- how to streamline it?
        self.userqueue = []
        self.userqueue_nsfw = []
        self.userqueue_trivia = []
        # might be necessary later to lay out more discriminators and do some more complex set logic
        self.calllist = {}

    async def check(self, state):
        guild = state.message.guild
        call = self.calllist.get(guild.id, None)
        is_cmd = state.message.content.startswith(state.host.prefix)  # TODO: do this elsewhere please
        if call and not is_cmd and call.check_channels(state.message.channel):
            await call.process_message(state)
        return self == state.command_host

    @Command.register(name="multitrivia")
    async def multitrivia(host, state):
        '''
Take on some trivia masters. Indiscriminate for now, until we get game chat working.

Plays a round of five questions, crowning the winning server by the percentage of correctly answered questions.

If a question is deleted, the server is penalized based on the maximum number of user submissions.

Penalties are present for low participation (avoiding difficult questions), so give it your best shot.'''
        print(host)
        USER_THRESHOLD = 2
        target = state.message.channel
        # TODO: implement this into a common method
        try:
            await target.send("*Added to call queue!*")  # check if we can post here -- if not, don't bother
        except Forbidden:
            print("call blocked due to permissions errors")
            return
        if state.command_host.calllist.get(state.message.guild.id, None):
            await target.send("You're already in a communication channel!")
            return

        valid_channels = state.command_host.userqueue_trivia
        for queueitem in valid_channels:
            if queueitem[1] == target.guild:
                await target.send("You're already waiting for a channel on this server!")
                return
        if len(valid_channels) >= (USER_THRESHOLD - 1):
            participant_list = [state.message]
            task_list = [asyncio.create_task(target.send("*The trivia game is about to begin!*"))]
            for i in range(USER_THRESHOLD - 1):
                msg = valid_channels.pop(0)[0]
                participant_list.append(msg)
                task_list.append(asyncio.create_task(msg.channel.send("*The trivia game is about to begin!*")))
            await asyncio.wait(task_list)  # ensure all channels have received this
            await asyncio.sleep(5)
            t_convo = TriviaConvo(state.command_host, participant_list, host)
            for msg in participant_list:
                state.command_host.calllist[msg.guild.id] = t_convo
        else:
            state.command_host.userqueue_trivia.append((state.message, target.guild))

    @Command.register(name="telephone")
    async def telephone(host, state):
        '''
Make some new friends across the web. NSFW/SFW channels are separated as well, so go nuts.

Usage:
g telephone
        '''
        target = state.message.channel
        # TODO: perform some db function to get a user's rep
        # users match with people with roughly their rating or lower
        # if no suitable matches, sit around and wait
        if target.nsfw:
            valid_channels = state.command_host.userqueue_nsfw
        else:
            valid_channels = state.command_host.userqueue
        for queueitem in valid_channels:
            if queueitem[1] == target.guild:
                await target.send("You're already waiting for a channel on this server!")
                return
        if state.command_host.calllist.get(state.message.guild.id, None):
            await target.send("You're already in a communication channel!")
            return
        try:
            await target.send("*Added to call queue!*")  # check if we can post here -- if not, don't bother
        except Forbidden:
            print("call blocked due to permissions errors")
            return
        # config
        if valid_channels:
            pardner = valid_channels.pop(0)[0]
            # TODO: better way to deliver this data and avoid the list comprehension step, maybe just storing the channel as a value to a guild list dict?
            c1 = asyncio.create_task(target.send("***Connected to a random place in cyberspace...***"))
            c2 = asyncio.create_task(pardner.send("***Connected to a random place in cyberspace...***"))

            await asyncio.wait([c1, c2])
            convo = Teleconvo(target, pardner, state.command_host)
            state.command_host.calllist[pardner.guild.id] = convo
            state.command_host.calllist[state.message.guild.id] = convo
            # task creation
        else:
            valid_channels.append((target, target.guild))

    @Command.register(name="hangup")
    async def hangup(host, state):
        '''
Hangs up the phone. Don't worry, the other person won't see it. Alternatively, removes you from the call queue.

Usage:
g hangup
        '''
        chan = state.message.channel
        call = state.command_host.calllist.get(chan.guild.id, None)
        if call and call.check_channels(chan):
            await call.end_call(chan)
        else:
            if chan.nsfw:
                valid_channels = state.command_host.userqueue_nsfw
            else:
                valid_channels = state.command_host.userqueue
            for q in valid_channels:
                if q[1] == chan.guild:
                    valid_channels.remove(q)
                    await chan.send("Removed from telephone queue.")
                    return
            for q in state.command_host.userqueue_trivia:
                if q[1] == chan.guild:
                    state.command_host.userqueue_trivia.remove(q)
                    await chan.send("Removed from trivia queue.")
                    return
            await chan.send("You are not in any queue!")
