from .base import Command, Module
from discord import Embed
import aiomysql
import random


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


class Fishing(Module):
    COMMAND_LIST = ("cast", "reel")
    LOCATIONS = ("LAKE", "RIVER", "OCEAN", "BEACH", "POND", "OASIS", "SPRING", "???")

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
        if subtype in Fishing.COMMAND_LIST:
            state.command_host[subtype](state, subcommand)
        else:
            await state.message.channel.send("That's not part of the fishing!")

    async def cast(self, state, args):
        # fetch user loadout from DB (skipping for now)
        descrip = ""
        for i in range(len(self.LOCATIONS)):
            descrip += f"\n{i}. {self.LOCATIONS[i]}"
        reaction_embed = Embed(title="Choose a location", description=descrip, color=0xa0fff0)
        locindex = await Command.add_reactions(state.message.channel, reaction_embed, state.host, answer_count=len(self.LOCATIONS), author=state.message.author)
        query = f"SELECT * FROM fishdb WHERE location = '{self.LOCATIONS[locindex]}'"
        async with state.host.db
        # simulate catch depth, delay, and species by fetching fish data from DB

        # kickstart an asynch delay process that will display a catch notification when ready

        # once this occurs, create a message and add reactions to it (async with timeout: if catch fails, display fail msg)
        pass

    async def shop(self, state, args):
        # display all list items

        # introduce an async while loop which delivers the desired item list until the user quits the store

        # on purchase, modify the user's loadout/stats
        pass
