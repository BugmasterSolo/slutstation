from .base import Module, Command
from discord import Status
import random
import math

'''
aiohttp:
    asynch http requests in line with what we would expect
    get it ready!
'''


class Fun(Module):
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
        print("ass")

    @Command.register(name="pushup")
    async def pushup(host, state):
        count = int(math.floor(float(state.args[1]) + 1))
        await state.message.channel.send(f"that's cool but i can do {count} pushups")
