from .base import Module, Command
import asyncio
import async_timeout
from discord.errors import Forbidden

# TODO: SERVER JEOPARDY! waiting out asyncs to allow servers to guess for an answer
# additionally: using telephone as scaffolding for multiplayer trivia

# todo: break up the convo

class Convo:
    def __init__(self, message1, message2, cmdhost):
        self.host = cmdhost
        self.end_a = {
            'channel': message1[0],
            'guild': message1[1]
        }

        self.end_b = {
            'channel': message2[0],
            'guild': message2[1]
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

    async def end_call(self):
        self.message_status.set()

        ta = asyncio.create_task(self.end_a['channel'].send("**Conversation closed.**"))
        tb = asyncio.create_task(self.end_b['channel'].send("**Conversation closed.**"))

        await asyncio.wait([ta, tb])

        self.host.calllist.pop(self.end_a['guild'].id)
        self.host.calllist.pop(self.end_b['guild'].id)
        print(self.host.calllist)


class Telephone(Module):
    # TODO: segregate sfw/nsfw
    def __init__(self, host):  # TODO: host instance not necessary
        super().__init__(self, host)
        # potentially managing hundreds of server connections at a time -- how to streamline it?
        self.userqueue = []
        self.userqueue_nsfw = []
        # might be necessary later to lay out more discriminators and do some more complex set logic
        self.calllist = {}

    async def check(self, state):
        guild = state.message.guild
        call = self.calllist.get(guild.id, None)
        is_cmd = state.message.content.startswith(state.host.prefix)  # TODO: do this elsewhere please
        if call and not is_cmd and call.check_channels(state.message.channel):
            await call.process_message(state)
        return self == state.command_host

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
        try:
            await target.send("*Added to call queue!*")  # check if we can post here -- if not, don't bother
        except Forbidden:
            print("call blocked due to permissions errors")
            return
        if state.command_host.calllist.get(state.message.guild.id, None):
            await target.send("You're already in a call here!")
            return
        # config
        if target.nsfw:
            valid_channels = state.command_host.userqueue_nsfw
        else:
            valid_channels = state.command_host.userqueue
        if (target, target.guild) in valid_channels:  # TODO: ehehe
            await target.send("You're already waiting for a call on this server!")
            return
        if valid_channels:
            pardner = state.command_host.userqueue.pop(0)
            # TODO: better way to deliver this data and avoid the list comprehension step, maybe just storing the channel as a value to a guild list dict?
            c1 = asyncio.create_task(target.send("***Connected to a random place in cyberspace...***"))
            c2 = asyncio.create_task(pardner.channel.send("***Connected to a random place in cyberspace...***"))

            await asyncio.wait([c1, c2])
            convo = Convo(state.message, pardner, state.command_host)
            state.command_host.calllist[pardner.guild.id] = convo
            state.command_host.calllist[state.message.guild.id] = convo
            # task creation
        else:
            state.command_host.userqueue.append((state.message.channel, state.message.guild))

    @Command.register(name="hangup")
    async def hangup(host, state):
        '''
Hangs up the phone. Don't worry, the other person won't see it. Alternatively, removes you from the call queue.

Usage:
g hangup
        '''
        call = state.command_host.calllist.get(state.message.guild.id, None)
        if call and call.check_channels(state.message.channel):
            await call.end_call()
        else:
            user_dupes = [m for m in state.command_host.userqueue if m[1].id == state.message.guild.id]  # TODO: ohoho
            if user_dupes:
                for m in user_dupes:
                    state.command_host.userqueue.remove(m)
                await state.message.channel.send("Removed from queue.")
            else:
                await state.message.channel.send("You are not in the message queue!")
