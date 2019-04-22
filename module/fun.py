from .base import Module, Command
from discord import Status, Embed

import time
import random
import json
import asyncio
import html

'''
aiohttp:
    asynch http requests in line with what we would expect
    get it ready!
'''


class Fun(Module):
    # probably runs on import, no longer needed.
    # also: this is a significant limitation of the current structure.
    # + i dont like it.
    FORTUNE_LIST = []
    TRIVIA_REACTION_LIST = ("\U0001F1F9", "\U0001F1EB", "\U0001F1E6", "\U0001F1E7", "\U0001F1E8", "\U0001F1E9")
    # referred to from host, with command_host this can be a module value
    with open("./module/module_resources/fortune_cookie.json", "r") as fortune:
        FORTUNE_LIST = json.loads(fortune.read())

    @Command.register(name="fortune", descrip="if you are going to die you should look here")
    async def fortune(host, state):  # if any issues come up check here.
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

    @Command.register(name="coinflip", descrip="flip a coin!")
    async def coinflip(host, state):
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
        count = int(float(state.args[1]) + 1)
        await state.message.channel.send(f"that's cool but i can do {count} pushups")

    @Command.register(name="roll")
    async def roll(host, state):
        '''Operators are added automatically, separated by spaces.
           4d6 5d9 1d12 +4 -3 = 4 rolls of 6 side + 5 rolls of 9 side + 1 roll of 12 side, add 4, subtract 3.'''
        state.args.pop(0)
        sum = 0
        try:
            for index in range(len(state.args) - 1):
                roll = state.args[index]
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
                    state.args[index] = int_roll
            await state.message.channel.send("Rolled " + " + ".join(state.args) + f" and got **{sum}!**")
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
    @Command.register(name="trivia")
    async def trivia(host, state):
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
            if type == "boolean":
                correct_index = 0 if triv['correct_answer'] is True else 1
                descrip = "*You have 20 seconds to answer the following question.*\n\nTrue or False:\n\n" + descrip
                # not worth breaking out of this if statement for two lines lol
                trivia_embed = Embed(title=f"{triv['category']} -- {triv['difficulty']}",
                                     description=descrip)
                msg = await chan.send(embed=trivia_embed)
                await msg.add_reaction(Fun.TRIVIA_REACTION_LIST[0])
                await msg.add_reaction(Fun.TRIVIA_REACTION_LIST[1])
            elif type == "multiple":
                answer_array = triv['incorrect_answers']
                correct_index = random.randint(0, len(answer_array))
                answer_array.insert(correct_index, triv['correct_answer'])
                # hopefully general case isn't too necessary (bad string concat)
                descrip = "*You have 20 seconds to answer the following question.*\n\n" + descrip + f"A) {answer_array[0]}\nB) {answer_array[1]}\nC) {answer_array[2]}\nD) {answer_array[3]}\n\n"
                correct_index += 2  # abcd stored two indices over in the emoji str tuple
                trivia_embed = Embed(title=f"{triv['category']} - {triv['difficulty']}",
                                     description=descrip,
                                     color=0x8050ff)
                msg = await chan.send(embed=trivia_embed)
                for i in range(2, 6):
                    await msg.add_reaction(Fun.TRIVIA_REACTION_LIST[i])
            await asyncio.sleep(10)
            warning = await chan.send("*10 seconds remaining!*")
            await asyncio.sleep(5)
            await warning.delete()
            await asyncio.sleep(5)
            # refresh the reaction list
            done = await chan.send("***Time's up!***")
            msg_reactions = await chan.fetch_message(msg.id)
            msg_reactions = msg_reactions.reactions
            correct_users = []
            incorrect_users = []
            for reaction in msg_reactions:
                if str(reaction.emoji) in Fun.TRIVIA_REACTION_LIST:
                    answer_index = Fun.TRIVIA_REACTION_LIST.index(str(reaction.emoji))
                    async for user in reaction.users():
                        if not user == host.user:
                            if answer_index == correct_index:
                                if user not in incorrect_users:
                                    print(str(user.name) + " answered correctly!")
                                    correct_users.append(user)
                            else:
                                if user in correct_users:
                                    print(str(user.name) + " cheated!")
                                    correct_users.remove(user)
                                else:
                                    print(str(user.name) + " was incorrect!")
                                    incorrect_users.append(user)
            await done.delete()
            if len(correct_users) == 0:
                await chan.send(f"Sorry, no one answered correctly.\nThe correct answer was {triv['correct_answer']}.")
            else:
                user_ids = map(lambda u: "<@" + str(u.id) + ">", correct_users)
                return_string = f"The correct answer was {triv['correct_answer']}!\n\nCongratulations to " + ", ".join(user_ids) + " for answering correctly!"
                await chan.send(return_string)
        else:
            chan.send("Could not fetch trivia questions from server.")

    # George Marsaglia, FSU. For cases in which state constancy matters, like the fortune cookie.
    def _xorshift(num):  # change back to absolute reference if not working
        tnum = num & 0xFFFFFFFF
        tnum = (tnum ^ (tnum << 13))
        tnum = (tnum ^ (tnum >> 17))
        tnum = (tnum ^ (tnum << 5))
        return tnum & 0xFFFFFFFF
