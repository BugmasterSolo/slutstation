from .base import Module, Command
from discord import Status, Embed

import time
import random
import json
import sys

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
    MAX_INT = sys.maxsize
    # referred to from host, with command_host this can be a module value
    with open("./module/module_resources/fortune_cookie.json", "r") as fortune:
        FORTUNE_LIST = json.loads(fortune.read())

    @Command.register(name="fortune", descrip="if you are going to die you should look here")
    async def fortune(host, state):  # if any issues come up check here.
        cur = int(time.time() / 86400)
        seed = state.command_host._xorshift(state.message.author.id - cur)
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
        flip = random.random()
        if flip < 0.02:
            randuser = None
            while True:
                randuser = random.choice(state.message.guild.members)
                if randuser.status == Status.online:
                    break
            randuser = randuser.id
            await state.message.channel.send(random.choice((
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
            await state.message.channel.send("You flipped heads!")
        else:
            await state.message.channel.send("You flipped tails!")

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

    # George Marsaglia, FSU. For cases in which state constancy matters, like the fortune cookie.
    def _xorshift(self, num):  # change back to absolute reference if not working
        num = num & self.MAX_INT
        return (num << 1) ^ (num >> 15) ^ (num << 4)
