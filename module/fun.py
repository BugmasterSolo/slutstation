from .base import Module, Command, Scope, MessageDeletedException
from discord import Status, Embed
# import mysql.connector as mysql

import time
import random
import json
import html
import re
from string import ascii_uppercase as letters
from discord.errors import NotFound, Forbidden


# TODO: Modify poll info to appear in embed message.
class Fun(Module):
    # probably runs on import, no longer needed.
    # also: this is a significant limitation of the current structure.
    # + i dont like it.
    MAX_INT = 4294967295
    FORTUNE_LIST = []
    TRIVIA_REACTION_LIST = ("\U0001F1F9", "\U0001F1EB", "\U0001f1e6", "\U0001f1e7", "\U0001f1e8", "\U0001f1e9")
    EIGHT_BALL = ("It is certain",
                  "It is decidedly so",
                  "Without a doubt",
                  "Sure, why not",
                  "Definitely",
                  "Yeah that sounds good",
                  "Outlook good",
                  "Signs point to yes",
                  "I guess so",
                  "It may result in your favor",
                  "I never doubted it",
                  "Don't count on it",
                  "The ether is telling me otherwise",
                  "Unlikely",
                  "Please do not count on it",
                  "You will not be pleased with the result",
                  "I'm very sorry")
    # referred to from host, with command_host this can be a module value
    with open("./module/module_resources/fortune_cookie.json", "r") as fortunes:
        FORTUNE_LIST = json.loads(fortunes.read())

    @Command.register(name="fortune")
    async def fortune(self, host, state):  # if any issues come up check here.
        '''
Tells your fortune. One fortune per day.

Usage:
g fortune
        '''
        cur = int(time.time() / 86400)
        seed = self._xorshift(state.message.author.id - cur)
        # eh
        seed %= len(Fun.FORTUNE_LIST)
        timeformat = time.strftime("%B %d, %Y", time.gmtime())
        description = f"Your fortune for {timeformat}:\n\n{Fun.FORTUNE_LIST[seed]}"
        fortune = Embed(title="Fortune",
                        type="rich",
                        color=0xE8522E,
                        description=description)
        await state.message.channel.send(embed=fortune)

    @Command.register(name="coinflip", alias=("flip"))
    async def coinflip(self, host, state):
        '''
Flips a coin that you can watch tumble in the air.

Usage:
g coinflip
        '''
        msg = state.message
        flip = random.random()
        if flip < 0.02:
            randuser = None
            while True:
                randuser = random.choice(msg.guild.members)
                if randuser.status == Status.online:
                    break
            randuser = randuser.id
            await msg.channel.send(random.choice((
                "The coin landed on its side!",
                "The coin penetrated the floor and shattered.",
                "The coin vanished instantly...",
                f"The coin struck <@{randuser}> in the head!",
                "father says to quiet down",
                "Sadly, your coin was thefted by a passerby.",
                f"<@{randuser}> stole the coin in a stunning display of dexterity!",
                "please stop asking me to flip coins"
            )))
        elif flip < 0.51:
            await msg.channel.send("You flipped heads!")
        else:
            await msg.channel.send("You flipped tails!")

    @Command.register(name="pushup")
    async def pushup(self, host, state):
        '''
A contest of wits.

Usage:
g pushup <int>
        '''
        args = host.split(state.content)
        if len(args) == 0:
            await state.message.channel.send("bro no flex")
            return
        try:
            count = int(float(args[0]) + 1)
        except ValueError:
            await state.message.channel.send("no digits? no time")
            return
        await state.message.channel.send(f"that's cool but i can do {count} pushups")

    @Command.register(name="roll")
    async def roll(self, host, state):
        '''Operators are added automatically, separated by spaces.
Usage:
g roll [dice1, dice2, ...]

Dice are specified as <number>d<sides>. Modifiers are provided as positive or negative integers: +4 = 4, -3 = -3.

Example:
g roll 3d6 2d20 -3 - three six-sided die + two 20-sided die - 3'''
        args = host.split(state.content)
        sum = 0
        try:
            for index in range(len(args)):
                roll = args[index]
                if "d" in roll:  # dice roll
                    rollstat = roll.split("d")
                    dicecount = int(rollstat[0])
                    rollmax = int(rollstat[1])
                    if dicecount > 4096 or rollmax > Fun.MAX_INT:
                        await state.message.channel.send("***whoa bud take it easy on the dice***")
                        # sure i mean it's close
                        raise OverflowError("Someone's trying to be a smartass.")
                    while dicecount > 0:
                        sum += random.randint(1, rollmax)
                        dicecount -= 1
                else:
                    int_roll = int(roll)
                    sum += int_roll
                    # fix display
                    args[index] = str(int_roll)
            await state.message.channel.send("Rolled " + " + ".join(args) + f" and got **{sum}!**")
        except Exception as e:
            # avoid double exception print
            if not isinstance(e, OverflowError):
                await state.message.channel.send("Invalid roll syntax provided.")
            print(e)

    @Command.register(name="uptime")
    async def uptime(self, host, state):
        '''Returns how long the bot has been running for since last reset.'''
        uptime = (time.time() - host.uptime) / 86400
        await state.message.channel.send(f"I have been active for {uptime:.2f} days so far!")

    @Command.cooldown(scope=Scope.CHANNEL, time=0, type=Scope.RUN)
    @Command.register(name="trivia")
    async def trivia(self, host, state):
        '''
Play a funky trivia game with your friends.

Usage: g trivia
        '''
        chan = state.message.channel
        correct_users, incorrect_users, triv = await host.tdb_trivia(state.message)
        if triv is not None:  # something went wrong
            # note: fix other none checks, oops
            if (state.message.author not in correct_users and state.message.author not in incorrect_users):
                incorrect_users.append(state.message.author)
            if len(correct_users) == 0:
                await chan.send(f"Sorry, no one answered correctly.\nThe correct answer was {html.unescape(triv['correct_answer'])}.")
            else:
                user_ids = map(lambda u: "<@" + str(u.id) + ">", correct_users)
                # answer array not dependable, we just have to reparse it for now

                # todo: fix that maybe if necessary
                return_string = f"The correct answer was {html.unescape(triv['correct_answer'])}!\n\nCongratulations to " + ", ".join(user_ids) + " for answering correctly!"
                await chan.send(return_string)
        # i dont like this very much but its ok
        # create a stack of awaitables to call?
        async with host.db.acquire() as conn:
            async with conn.cursor() as cur:
                for user in correct_users:
                    await cur.callproc("TRIVIACALL", (True, user.id))
                for user in incorrect_users:
                    await cur.callproc("TRIVIACALL", (False, user.id))
            await conn.commit()  # im retadad

    @Command.cooldown(scope=Scope.CHANNEL, time=10, type=Scope.TIME)
    @Command.register(name="poll")
    async def poll(self, host, state):
        '''
Run a poll in your current server.

Usage:
g poll \"<question (in quotes)>\" <duration int (seconds)> <choiceA> | <choiceB> | ...

Bot will send reminder messages every few, with a link to the message.

Prints the final results at the end of the poll!
        '''
        chan = state.message.channel
        msg = state.content
        question = None
        timer = None
        end_index = None
        quote = None
        if len(msg) <= 0:
            await chan.send("`Unformatted poll. Add a question first!`")
            return
        if msg[0] in host.QUOTE_TYPES:  # user passed a question string
            quote = host.get_closing_quote(msg[0])
            end_index = msg.find(quote, 1)
            if end_index == -1:
                await chan.send("Unclosed quote, sorry bud :(")
                return
            question = msg[1:end_index]
        else:
            await chan.send("Please put your questions in quotes or I can't find them.")
            return
        msg = msg[end_index + 1:].strip()
        end_index = msg.find(" ")
        try:
            timer = int(msg[:end_index])
            msg = msg[end_index + 1:].strip()
            if timer < 0:
                await chan.send("alright smartass cut it with the negative polls")
                return
        except Exception as e:
            timer = 30
            print(e)
        answer_list = re.split(r"\s*\|\s*", msg)
        answer_count = len(answer_list)
        if answer_count <= 0:
            await chan.send("Please provide your poll with some possible responses!")
            return
        description = "*Duration: " + host.format_duration(timer) + "*\n\n"
        for i in range(answer_count):
            description += letters[i] + f") {answer_list[i]}\n"
        description += "\n*Created on " + time.strftime("%B %d %Y, %H:%M:%S ", time.gmtime()) + "UTC*"
        question_embed = Embed(title=question, description=description, color=0x8050ff)
        try:
            poll_id = await host.add_reactions(chan, question_embed, timer, answer_count=answer_count, descrip=question)
        except MessageDeletedException:
            await chan.send(f"The poll for *{question}* was deleted.")
        poll = await chan.fetch_message(poll_id)
        poll_reactions = poll.reactions
        poll_responses = [None] * answer_count
        counted_users = []
        for emoji in poll_reactions:
            emoji_string = str(emoji)
            if not emoji.custom_emoji:
                unicode = ord(emoji_string) - host.A_EMOJI
                if unicode < answer_count and unicode >= 0:
                    tally = 0
                    # switch to IDs.
                    async for user in emoji.users():
                        if not user == host.user and user.id not in counted_users:
                            counted_users.append(user.id)
                            tally += 1
                    poll_responses[unicode] = tally
        max = 0
        maxindex = [0]
        for i in range(answer_count):
            tally = poll_responses[i]
            if tally > max:
                maxindex = [i]
                max = tally
            elif tally == max:
                maxindex.append(i)
        # deal with tie case
        result_string = None
        if max == 0:
            result_string = "*No one voted on this poll... :(*"
        else:
            if len(maxindex) == 1:
                result_string = f"*Result: '{answer_list[maxindex[0]]}' won with {max} vote(s)!*"
            else:
                top_answers = ", ".join(map(lambda i: answer_list[i], maxindex))
                result_string = f"***Result: '{top_answers}' tied with {max} vote(s)!***"
            poll_summary = "\n\n"
            for i in range(answer_count):
                percent = "{:.2f}".format(100 * poll_responses[i] / len(counted_users))
                answer_summary = f"{answer_list[i]} -- {poll_responses[i]} vote(s) ({percent}%)"
                if i in maxindex:
                    answer_summary = f"***{answer_summary}***"
                poll_summary += f"{answer_summary}\n\n"
            result_string += poll_summary + poll.jump_url
        await chan.send(result_string)
        await poll.edit(content=result_string)

    @Command.register(name="8ball")
    async def eightball(self, host, state):
        '''
Funny little 8ball game for you and friends.
        '''
        if len(state.content) <= 0:
            await state.message.channel.send("Please ask a question before harnessing the 8ball!")
            return
        await state.message.channel.send("\U0001f3b1 | *" + random.choice(Fun.EIGHT_BALL) + "...*")

    @Command.register(name="night")
    async def night(self, host, state):
        '''Wishes you a healthy goodnight message.'''
        msg = state.message
        target = None
        if len(msg.mentions) > 0:
            target = msg.mentions[0]
        if target == host.user:
            target = msg.author
        if target:
            await msg.channel.send(f"Good night <@{target.id}>!")
        else:
            await msg.channel.send("Good night!")

    # desc's are not necessary for short queries, such as trivia.
    # todo: move into host.

    @Command.register(name="help")
    async def help(self, host, state):
        '''Hey that's me'''
        await state.message.channel.send("http://baboo.mobi/government/help/")

    @Command.register(name="undo")
    async def undo(self, host, state):
        '''For big mistakes. Deletes 1 or more valid results (and their associated commands) from the message log. Undos are handled by individual commands. Check the help section to see if you can undo a command!

The logger stores up to 50 commands per channel.

Usage: g undo <#>
'''
        chan = state.message.channel
        undo_log = host.undo_log.get(chan.id)
        delete_count = 1
        if state.message.author.permissions_in(chan).administrator:
            try:
                delete_count = max(int(state.content), 1)
            except ValueError:
                pass
        if undo_log:
            msg_cache = []
            for _ in range(delete_count):
                try:
                    msg_list = undo_log.pop()
                    for m in msg_list:
                        msg_cache.append(m)
                except IndexError:
                    await chan.send("Undo history cleared.", delete_after=5)
                    return
            try:
                await chan.delete_messages(msg_cache)
            except Forbidden:
                pass
            await chan.send(f"{delete_count} message(s) deleted.", delete_after=5)
        else:
            await chan.send("No undoable messages on record.", delete_after=5)
        try:
            await state.message.delete()
        except Forbidden:
            pass

    # 32 bit xorshift. used for state dependent PRNG.
    def _xorshift(self, num):
        tnum = num & 0xFFFFFFFF
        tnum = (tnum ^ (tnum << 13))
        tnum = (tnum ^ (tnum >> 17))
        tnum = (tnum ^ (tnum << 5))
        return tnum & 0xFFFFFFFF
