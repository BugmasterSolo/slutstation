from .base import Command, Module, Scope
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


class Bait(FishingItem):
    def __init__(self, name, descrip, price, *args, **fish_conditions):
        super().__init__(name, descrip, price)


class Lure(FishingItem):
    pass


class Trap(FishingItem):
    pass


class Fishing(Module):
    CAST_COST = 10
    COMMAND_LIST = ("cast")
    LOCATIONS = ("LAKE", "RIVER", "OCEAN", "BEACH", "POND", "OASIS", "SPRING", "???")
    LOC_PRINT = ("Century Lake", "River Delta", "Open Ocean", "The Shorelines", "Secluded Pond", "Desert Oasis", "Somewhere deep in the High Alpines", "???")
    LOC_EMOJI = ("\U0001f4a7", "\U0001f32b", "\U0001f30a", "\U0001f3d6", "\U0001f986", "\U0001f3dd", "\U0001f304", "\U0001f308")
    RARITY_STRING = ("```\nCommon\n```", "```CSS\nUncommon\n```", "```ini\n[Rare]\n```", "```fix\nUltra Rare\n```", "```diff\n-Legendary\n```")

    # me and the boys going fishing
    @Command.cooldown(scope=Scope.USER, time=0, type=Scope.RUN)
    @Command.register(name="fish")
    async def fish(self, host, state):
        '''
        Initializes a command relating to fishing. The following commands are currently available:
g fish cast - Casts the fishing line at a chosen location.
        '''
        subcommand = host.split(state.content)
        try:
            subtype = subcommand.pop(0)
        except IndexError:
            await state.message.channel.send("Please input a subcommand: `g fish <cast, reel, ...>`")
            return
        if subtype in Fishing.COMMAND_LIST:
            await getattr(self, subtype)(host, state, subcommand)
        else:
            await state.message.channel.send("That's not part of the fishing!")

    async def cast(self, host, state, args):
        # fetch user loadout from DB (skipping for now)
        auth = state.message.author
        descrip = "```"
        for i in range(len(self.LOCATIONS)):
            descrip += f"\n{chr(i + 0x41)}. {self.LOC_PRINT[i]} | {self.CAST_COST}{host.CURRENCY_SYMBOL}"
        descrip += "```"
        reaction_embed = Embed(title="Choose a location:", description=descrip, color=0xa0fff0)
        locindex = await host.add_reactions(state.message.channel, reaction_embed, answer_count=len(self.LOCATIONS), author=auth)
        if locindex == -1:
            await state.message.channel.send("`Fishing cancelled -- response not sent in time.`")
        target = None
        cast_msg = await state.message.channel.send(f"{self.LOC_EMOJI[locindex]} | ***Casting...***")
        async with host.db.acquire() as conn:
            async with conn.cursor() as cur:
                if not await host.spendcredits(cur, auth.id, Fishing.CAST_COST):
                    await state.message.channel.send("You do not have enough credits!")
                    return
                await cur.callproc('GETFISH', (1, 1, self.LOCATIONS[locindex]))
                target = await cur.fetchone()
                distro = random.gauss(0, 1)
                maxlog = math.log(target[5])
                minlog = math.log(target[4])
                stdev = float(maxlog - minlog) / 4
                mean = float(maxlog + minlog) / 2
                size = math.e ** (mean + stdev * distro)
                percentile = cdf_normal(distro) * 100
                rarity = self.RARITY_STRING[target[6] - 1]
                label = "n" if target[1] in 'aeiou' else ""
                embed_catch = Embed(title=f"{self.LOC_EMOJI[locindex]} | *It's big catch!*",
                                    description="You just caught a{1} {0[1]}!\n\n*{0[2]}*\n\n**Length:** {2:.2f}cm\n*Larger than {3:.4g}% of all {0[1]}!*\n\n**Price:** {0[8]}{5}\n\n{4}".format(target, label, size, percentile, rarity, host.CURRENCY_SYMBOL),
                                    color=0xa0fff0)
                embed_catch.set_footer(text=f"Caught by {auth.name}#{auth.discriminator}", icon_url=auth.avatar_url_as(format="png", size=128))
                interval = random.uniform(5, 9)
                await cur.callproc('GIVE_CREDITS', (state.message.author.id, target[8]))
            await conn.commit()
        await asyncio.sleep(interval)
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
