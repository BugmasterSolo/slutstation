from .base import Command, Module
from discord import Embed
import random
import asyncio
import math


class FishingItem:
    CURRENCY_SYMBOL = "฿"

    def __init__(self, name, descrip, price):
        self.name = name
        self.descrip = descrip
        self.price = price

    def buy(self, currency):
        return self.price <= currency

    def get_embed(self):
        embed = Embed(title=self.name,
                      description=self.descrip,
                      color=0xa0fff0)
        embed.set_footer(text=f"Price: {self.price}{self.CURRENCY_SYMBOL}")
        return embed


class Line(FishingItem):
    def __init__(self, name, descrip, price, length, strength):
        FishingItem.__init__(self, name, descrip, price)
        self.length = length
        self.strength = strength

    def get_line_success(self, weight):
        if weight <= self.strength:
            return True
        else:
            chance = self.strength / 4 * (weight - self.strength) + self.strength
        return random.random() < chance


class FishingAttractor:
    def __init__(self, *args, **fish_conditions):
        self.conditions = {}
        for arg in fish_conditions:
            self.conditions[arg] = fish_conditions[arg]
        pass


class Bait(FishingItem):
    def __init__(self, name, descrip, price, *args, **fish_conditions):
        super().__init__(name, descrip, price)


class Lure(FishingItem):
    pass

class Trap(FishingItem):
    pass


class Fishing(Module):
    COMMAND_LIST = ("cast", "reel")
    LOCATIONS = ("LAKE", "RIVER", "OCEAN", "BEACH", "POND", "OASIS", "SPRING", "???")
    LOC_PRINT = ("Century Lake", "River Delta", "Open Ocean", "The Shorelines", "Secluded Pond", "Desert Oasis", "Somewhere deep in the High Alpines", "???")
    LOC_EMOJI = ("\U0001f4a7", "\U0001f3d3", "\U0001f30a", "\U0001f3d6", "\U0001f986", "\U0001f3dd", "\U0001f304", "\U0001f308")

    # me and the boys going fishing
    @Command.register(name="fish")
    async def fish(host, state):
        '''
        Initializes a command relating to fishing.
        '''
        subcommand = Command.split(state.content)
        try:
            subtype = subcommand.pop(0)
        except IndexError:
            await state.message.channel.send("Please input a subcommand: `g fish <cast, reel, ...>`")
            return
        if subtype in Fishing.COMMAND_LIST:
            await getattr(state.command_host, subtype)(state, subcommand)
        else:
            await state.message.channel.send("That's not part of the fishing!")

    async def cast(self, state, args):
        # fetch user loadout from DB (skipping for now)
        descrip = "```"
        for i in range(len(self.LOCATIONS)):
            descrip += f"\n{chr(i + 0x41)}. {self.LOC_PRINT[i]}"
        descrip += "```"
        reaction_embed = Embed(title="Choose a location:", description=descrip, color=0xa0fff0)
        locindex = await Command.add_reactions(state.message.channel, reaction_embed, state.host, answer_count=len(self.LOCATIONS), author=state.message.author)
        query = f"SELECT * FROM fishdb WHERE location = '{self.LOCATIONS[locindex]}'"
        res = None
        cast_msg = await state.message.channel.send(f"{self.LOC_EMOJI[locindex]} | *Casting...*")
        async with state.host.db.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query)
                res = await cur.fetchall()
        catch_value = random.random() * 100
        catch_sum = 0
        pos = 0
        while True:
            catch_sum += res[pos][7]
            if catch_sum > catch_value:
                break
            pos += 1
        if (pos > len(res)):
            pos = len(res) - 1
        target = res[pos]
        distro = random.gauss(0, 1)
        stdev = float(target[5] - target[4]) / 4
        mean = float(target[5] + target[4]) / 2
        size = mean + stdev * distro
        percentile = cdf_normal(distro) * 100
        label = "n" if target[1] in 'aeiou' else ""
        embed_catch = Embed(title=f"{self.LOC_EMOJI[locindex]} | *It's big catch!*",
                            description="You just caught a{1} {0[1]}!\n\n*{0[2]}*\n\n**Length:** {2:.2f}cm\n*Larger than {3:.2g}% of all {0[1]}!*".format(target, label, size, percentile),
                            color=0xa0fff0)
        await asyncio.sleep(random.uniform(5, 9))
        await cast_msg.delete()
        await state.message.channel.send(embed=embed_catch)


    async def shop(self, state, args):
        # display all list items

        # introduce an async while loop which delivers the desired item list until the user quits the store

        # on purchase, modify the user's loadout/stats
        pass


def cdf_normal(z):
    # from python docs: https://docs.python.org/3/library/math.html
    return (1.0 + math.erf(z / math.sqrt(2))) / 2
