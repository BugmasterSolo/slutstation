from .base import Module, Command
from discord import Status, Embed

import time
import random
import math
import json
import sys

'''
aiohttp:
    asynch http requests in line with what we would expect
    get it ready!
'''


class Fun(Module):
    # probably runs on import, no longer needed.\
    # also: this is a significant limitation of the current structure.
    # + i dont like it.
    FORTUNE_LIST = []
    MAX_INT = sys.maxsize
    with open("./module/module_resources/fortune_cookie.json", "r") as fortune:
        FORTUNE_LIST = json.loads(fortune.read())

    @Command.register(name="fortune", descrip="read")
    async def fortune(host, state):
        cur = int(time.time() / 86400)
        print(cur)
        seed = Fun._xorshift(state.message.author.id - cur)
        # eh
        seed %= len(Fun.FORTUNE_LIST)
        timeformat = time.strftime("%B %d, %Y")
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
        count = int(math.floor(float(state.args[1]) + 1))
        await state.message.channel.send(f"that's cool but i can do {count} pushups")

    # George Marsaglia, FSU.
    def _xorshift(num):
        num = num & Fun.MAX_INT
        return (num << 1) ^ (num >> 15) ^ (num << 4)
