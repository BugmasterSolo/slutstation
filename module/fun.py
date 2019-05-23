from .base import Module, Command, Scope
from discord import Status, Embed
# import mysql.connector as mysql

import time
import math
import random
import json
import asyncio
import html
import re
from string import ascii_uppercase as letters


# TODO: Modify poll info to appear in embed message.
class Fun(Module):
    # probably runs on import, no longer needed.
    # also: this is a significant limitation of the current structure.
    # + i dont like it.
    MAX_INT = 4294967295
    A_EMOJI = 0x0001F1E6
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
    with open("./module/module_resources/fortune_cookie.json", "r") as fortune:
        FORTUNE_LIST = json.loads(fortune.read())

    @Command.register(name="fortune")
    async def fortune(host, state):  # if any issues come up check here.
        '''
Tells your fortune. One fortune per day.

Usage:
g fortune
        '''
        cur = int(time.time() / 86400)
        seed = Fun._xorshift(state.message.author.id - cur)
        # eh
        seed %= len(Fun.FORTUNE_LIST)
        timeformat = time.strftime("%B %d, %Y", time.gmtime())
        description = f"Your fortune for {timeformat}:\n\n{Fun.FORTUNE_LIST[seed]}"
        fortune = Embed(title="Fortune",
                        type="rich",
                        color=0xE8522E,
                        description=description)
        await state.message.channel.send(embed=fortune)

    @Command.register(name="coinflip")
    async def coinflip(host, state):
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
    async def pushup(host, state):
        '''
A contest of wits.

Usage:
g pushup <int>
        '''
        args = Command.split(state.content)
        count = int(float(args[0]) + 1)
        await state.message.channel.send(f"that's cool but i can do {count} pushups")

    @Command.register(name="roll")
    async def roll(host, state):
        '''Operators are added automatically, separated by spaces.
Usage:
g roll [dice1, dice2, ...]

Dice are specified as <number>d<sides>. Modifiers are provided as positive or negative integers: +4 = 4, -3 = -3.'''
        args = Command.split(state.content)
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
    async def uptime(host, state):
        uptime = (time.time() - host.uptime) / 86400
        await state.message.channel.send(f"I have been active for {uptime:.2f} days so far!")

    # TODO: Integrate into economy. Potentially add a list of modules to the state? Allowing cogs to communicate.
    #       - Related: Implement cooldowns. Provide a special case for cooldowns (for instance, in the trivia case:
    #                  money questions would only be usable once every 15 mins or so, otherwise it would be for fun)
    #       - Add an elimination mode for larger servers (far future) in which users would be eliminated from the player pool
    #         for answering incorrectly. Some reward would then be given to the last m(a/e)n standing
    #           - Would be extremely fun to run this for all connected servers, with a collective jackpot for all users (hq trivia)
    #       - Add cooldown (min 20 seconds)
    #       - Modify trivia around cooldown -- trivia should be able to run based on its cooldown.
    #       - add cooldown in, but have a Trivia module that keeps track of the time since last "Money Q".
    #       - unfortunately this requires an extra time check outside of the cooldown scope, but that's fine in this 1/1000 case.
    # https://opentdb.com/api.php?amount=10&category=17
    @Command.cooldown(scope=Scope.CHANNEL, time=0, type=Scope.RUN)
    @Command.register(name="trivia")
    async def trivia(host, state):
        '''
Play a funky trivia game with your friends.

Usage: g trivia
        '''
        chan = state.message.channel
        url = "https://opentdb.com/api.php?amount=1"
        response = await Module._http_get_request(url)
        status = response['status']
        if status >= 200 and status < 300:
            triv = json.loads(response['text'])['results'][0]
            descrip = html.unescape(f"{triv['question']}\n\n")
            type = triv['type']
            correct_index = None
            msg = None
            # TODO: reduce diffeerences
            if type == "boolean":
                correct_index = 0 if triv['correct_answer'] == "True" else 1
                descrip = "*You have 20 seconds to answer the following question.*\n\nTrue or False:\n\n" + descrip
                trivia_embed = Embed(title=f"{triv['category']} -- {triv['difficulty']}",
                                     description=descrip,
                                     color=0x8050ff)
                trivia_embed.set_footer(text="Questions Provided by Open Trivia DB")
                char_list = [Fun.TRIVIA_REACTION_LIST[0], Fun.TRIVIA_REACTION_LIST[1]]  # what
                msg = await Fun.add_reactions(chan, trivia_embed, 20, loop=range(2), char_list=char_list)
            elif type == "multiple":
                answer_array = triv['incorrect_answers']
                correct_index = random.randint(0, len(answer_array))
                answer_array.insert(correct_index, triv['correct_answer'])
                answer_array = list(map(html.unescape, answer_array))
                descrip = "*You have 20 seconds to answer the following question.*\n\n" + descrip + f"A) {answer_array[0]}\nB) {answer_array[1]}\nC) {answer_array[2]}\nD) {answer_array[3]}\n\n"
                #
                #
                # use the unicode constant for this?
                #
                #
                correct_index += 2
                trivia_embed = Embed(title=f"{triv['category']} - {triv['difficulty']}",
                                     description=descrip,
                                     color=0x8050ff)
                trivia_embed.set_footer(text="Questions Provided by Open Trivia DB")
                msg = await Fun.add_reactions(chan, trivia_embed, 20, loop=range(4))
            # refresh the reaction list
            done = await chan.send("***Time's up!***")
            msg_reactions = await chan.fetch_message(msg)
            msg_reactions = msg_reactions.reactions
            correct_users = []
            incorrect_users = []
            for reaction in msg_reactions:
                if str(reaction) in Fun.TRIVIA_REACTION_LIST:
                    answer_index = Fun.TRIVIA_REACTION_LIST.index(str(reaction))
                    async for user in reaction.users():
                        if not user == host.user:
                            if answer_index == correct_index:
                                if user not in incorrect_users:
                                    correct_users.append(user)
                            else:
                                if user in correct_users:
                                    correct_users.remove(user)
                                    incorrect_users.append(user)
                                else:
                                    incorrect_users.append(user)
            await done.delete()
            if len(correct_users) == 0:
                await chan.send(f"Sorry, no one answered correctly.\nThe correct answer was {html.unescape(triv['correct_answer'])}.")
            else:
                user_ids = map(lambda u: "<@" + str(u.id) + ">", correct_users)
                # answer array not dependable, we just have to reparse it for now

                # todo: fix that maybe if necessary
                return_string = f"The correct answer was {html.unescape(triv['correct_answer'])}!\n\nCongratulations to " + ", ".join(user_ids) + " for answering correctly!"
                await chan.send(return_string)
            # this is at the end so it can all occur behind the scenes
            async with host.db.acquire() as conn:
                async with conn.cursor() as cur:
                    for user in correct_users:
                        await cur.callproc("TRIVIACALL", (True, user.id))
                    for user in incorrect_users:
                        await cur.callproc("TRIVIACALL", (False, user.id))
                await conn.commit()  # im retadad
        else:
            chan.send("Could not fetch trivia questions from server.")

    # todo:
    #   - probably keep trying to reduce cyclomatic complexity (if necessary)
    #   - add time of creation + duration to the poll embed
    @Command.cooldown(scope=Scope.CHANNEL, time=10, type=Scope.TIME)
    @Command.register(name="poll")
    async def poll(host, state):
        '''
Run a poll in your current server.

Usage:
g poll "<question>" <duration int (seconds)> <choiceA> | <choiceB> | ...
        '''
        chan = state.message.channel
        msg = state.content
        question = None
        timer = None
        end_index = None
        quote = None
        if len(msg) <= 0:
            await chan.send("Unformatted poll. Add a question first!")
            return
        if msg[0] in Fun.QUOTE_TYPES:  # user passed a question string
            quote = Module.get_closing_quote(msg[0])
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
        answer_list = re.split("\s*\|\s*", msg)
        answer_count = len(answer_list)
        if answer_count <= 0:
            await chan.send("Please provide your poll with some possible responses!")
            return
        loop_list = range(0, answer_count)
        description = "*Duration: " + Fun.format_duration(timer) + "*\n\n"
        for i in loop_list:
            description += letters[i] + f") {answer_list[i]}\n"
        description += "\n*Created on " + time.strftime("%B %d %Y, %H:%M:%S ", time.gmtime()) + "UTC*"
        question_embed = Embed(title=question, description=description, color=0x8050ff)
        poll_id = await Fun.add_reactions(chan, question_embed, timer, loop_list, descrip=question)
        poll = await chan.fetch_message(poll_id)
        poll_reactions = poll.reactions
        poll_responses = [None] * answer_count
        counted_users = []
        for emoji in poll_reactions:
            emoji_string = str(emoji)
            if not emoji_string.startswith("<"):  # is not custom
                unicode = ord(emoji_string) - Fun.A_EMOJI
                if unicode < answer_count:
                    tally = 0
                    # switch to IDs.
                    async for user in emoji.users():
                        if not user == host.user and user.id not in counted_users:
                            counted_users.append(user.id)
                            tally += 1
                    poll_responses[unicode] = tally
        max = 0
        maxindex = [0]
        for i in loop_list:
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
        elif len(maxindex) == 1:
            result_string = f"***Result: '{answer_list[maxindex[0]]}' won with {max} votes!***"
        else:
            top_answers = ", ".join(map(lambda i: answer_list[i], maxindex))
            result_string = f"***Result: '{top_answers}' tied with {max} votes!***"
        notify = await chan.send(result_string)
        await asyncio.sleep(5)
        await notify.delete()
        await poll.edit(content=result_string)

    @Command.register(name="8ball")
    async def eightball(host, state):
        '''
Funny little 8ball game for you and friends.
        '''
        if len(state.content) <= 0:
            await state.message.channel.send("Please ask a question before harnessing the 8ball!")
            return
        await state.message.channel.send("\U0001f3b1 | *" + random.choice(Fun.EIGHT_BALL) + "...*")

    # desc's are not necessary for short queries, such as trivia.
    async def add_reactions(chan, embed, timer, loop=None, char_list=None, descrip="Get your answer in!"):
        poll = await chan.send(embed=embed)
        # specifics!
        if char_list:
            for emote in char_list:
                await poll.add_reaction(emote)
        else:
            for i in loop:
                await poll.add_reaction(chr(Fun.A_EMOJI + i))
        # more dynamic response
        if timer >= 3600:
            await asyncio.sleep(timer - 1800)
            warning = await chan.send(f"***30 minutes remaining: '{descrip}'***")
            await asyncio.sleep(60)
            await warning.delete()
            timer = 1740
        if timer >= 900:
            await asyncio.sleep(timer - 600)
            warning = await chan.send(f"***10 minutes remaining: '{descrip}'***")
            await asyncio.sleep(30)
            await warning.delete()
            timer = 570
        if timer >= 300:
            await asyncio.sleep(timer - 180)
            warning = await chan.send("***3 minutes remaining!***")
            await asyncio.sleep(5)
            await warning.delete()
            timer = 175
        if timer >= 120:
            await asyncio.sleep(timer - 60)
            warning = await chan.send("***1 minute remaining!***")
            await asyncio.sleep(5)
            await warning.delete()
            timer = 55
        if timer > 10:
            await asyncio.sleep(timer - 10)
            # use a description on longer waits
            warning = await chan.send("***10 seconds remaining!***")
            await asyncio.sleep(5)
            await warning.delete()
            await asyncio.sleep(5)
        return poll.id
        # jump back into loop

    def format_duration(timer):
        duration_string = ""
        if (timer > 86400):
            day_count = math.floor(timer / 84600)
            timer = (timer - (day_count * 86400))
            duration_string += str(day_count) + " day" + ("s" if day_count > 1 else "")  # i dont like this
            if not (timer == 0):
                duration_string += ", "
        if (timer > 3600):
            hour_count = math.floor(timer / 3600)
            timer = (timer - (hour_count * 3600))
            duration_string += str(hour_count) + " hour" + ("s" if hour_count > 1 else "")
            if not (timer == 0):
                duration_string += ", "
        if (timer > 60):
            minute_count = math.floor(timer / 60)
            timer = (timer - (minute_count * 60))
            duration_string += str(minute_count) + " minute" + ("s" if minute_count > 1 else "")
            if not (timer == 0):
                duration_string += ", "
        if (timer > 0):
            duration_string += str(timer) + " second" + ("s" if timer > 1 else "")
        return duration_string

    # 32 bit xorshift. used for state dependent PRNG.
    def _xorshift(num):
        tnum = num & 0xFFFFFFFF
        tnum = (tnum ^ (tnum << 13))
        tnum = (tnum ^ (tnum >> 17))
        tnum = (tnum ^ (tnum << 5))
        return tnum & 0xFFFFFFFF
