from .base import Command, Module, Scope, MessageDeletedException
from discord import Embed
import random
import asyncio
from async_timeout import timeout
import time
import math
import collections

class Trap:
    __slots__ = ("location", "start_time", "duration", "owner", "server", "timer", "host", "gov", "public", "isclaimed")

    def __init__(self, location, start, duration, user, gid, host, gov):
        self.location = location
        self.start_time = start
        self.duration = duration
        self.owner = user
        self.server = gid
        self.host = host
        self.gov = gov
        self.public = False
        self.isclaimed = False
        self.timer = asyncio.Event()
        self.timer.clear()

        asyncio.create_task(self.waitforcatch())

    # belongs to user initially
    # after timeout, belongs to server. maxed after duration.
    #

    async def catch(self, owner):
        self.host.trap_list.pop(self.owner.id)
        self.timer.set()
        elapsed = min(time.time() - self.start_time, self.duration)
        catch_count = int((1 + (elapsed / self.duration)) ** 4) * (random.random() * 0.3 + 0.8)

        descrip = f"You caught {catch_count} fish!\n\n"
        pull = 0

        async with self.gov.db.acquire() as conn:
            async with conn.cursor() as cur:
                for i in range(catch_count):
                    size, percentile, rarity, _, price, name, _ = self.host.getfish(cur, self.location)
                    descrip += f"{i}. {name}\n\t{size:.2f}cm -- {percentile:.4g}%\n{rarity}\n\n"
                    pull += price
                await cur.callproc('GIVE_CREDITS', (owner.id, pull))

        return_embed = Embed(title="Trap fetched!", description=descrip, color=0xa0fff0)
        if owner == self.owner:
            self.host.trap_list.pop(self.owner.id)
        elif self.public:
            return_embed.set_footer(text=f"Stolen from {owner.name}#{owner.discriminator}", icon_url=owner.avatar_url_as(format="png", size=128))  
        return return_embed
        
            

    async def waitforcatch(self):
        try:
            async with timeout(self.duration):
                await self.timer.wait()
        except TimeoutError:
            self.public = True
            server_traps = self.host.server_traps.get(self.server, None)
            if server_traps is None:
                server_traps = self.host.server_traps[self.server] = collections.deque()
            server_traps.append(self)


class Fishing(Module):
    COMMAND_LIST = ("cast", "trap")
    LOCATIONS = ("LAKE", "RIVER", "OCEAN", "BEACH", "POND", "OASIS", "SPRING", "???")
    LOC_PRICES = (10, 10, 20, 25, 30, 50, 100, 500)
    LOC_PRINT = ("Century Lake", "River Delta", "Open Ocean", "The Shorelines", "Secluded Pond", "Desert Oasis", "Somewhere deep in the High Alpines", "???")
    LOC_EMOJI = ("\U0001f4a7", "\U0001f32b", "\U0001f30a", "\U0001f3d6", "\U0001f986", "\U0001f3dd", "\U0001f304", "\U0001f308")
    RARITY_STRING = ("```\nCommon\n```", "```CSS\nUncommon\n```", "```ini\n[Rare]\n```", "```fix\nUltra Rare\n```", "```diff\n-Legendary\n```")

    def __init__(self, host, *args, **kwargs):
        super().__init__(host, *args, **kwargs)
        self.trap_list = {}     # traps - user
        self.server_traps = {}  # traps, server -- keeps track of expired traps at a given server
        pass

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

    async def getfish(self, cur, loc):
        await cur.callproc('GETFISH', (1, 1, self.LOCATIONS[loc]))
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
        price = int(target[8] * self.LOC_PRICES[loc] / 10)
        return (size, percentile, rarity, label, price, target[1], target[2])

    async def pick_location(self, host, auth, chan, mult=1):
        descrip = "```"
        for i in range(len(self.LOCATIONS)):
            descrip += f"\n{chr(i + 0x41)}. {self.LOC_PRINT[i]} | {self.LOC_PRICES[i] * mult}{host.CURRENCY_SYMBOL}"
        descrip += "```"
        reaction_embed = Embed(title="Choose a location:", description=descrip, color=0xa0fff0)
        return await host.add_reactions(chan, reaction_embed, answer_count=len(self.LOCATIONS), author=auth)


    async def cast(self, host, state, args):
        # fetch user loadout from DB (skipping for now)
        auth = state.message.author
        try:
            locindex = self.pick_location(host, auth, state.message.channel)
        except MessageDeletedException:
            return
        if locindex == -1:
            await state.message.channel.send("`Fishing cancelled -- response not sent in time.`")
            return
        async with host.db.acquire() as conn:
            async with conn.cursor() as cur:
                if not await host.spendcredits(cur, auth.id, self.LOC_PRICES[locindex]):
                    await state.message.channel.send("You do not have enough credits!")
                    return
                cast_msg = await state.message.channel.send(f"{self.LOC_EMOJI[locindex]} | ***Casting...***")
                size, percentile, rarity, label, price, name, desc = await self.getfish(cur, locindex)

                embed_catch = Embed(title=f"{self.LOC_EMOJI[locindex]} | *It's big catch!*",
                                    description="You just caught a{1} {0}!\n\n*{7}*\n\n**Length:** {2:.2f}cm\n*Larger than {3:.4g}% of all {0}!*\n\n**Price:** {6}{5}\n\n{4}".format(name, label, size, percentile, rarity, host.CURRENCY_SYMBOL, price, desc),
                                    color=0xa0fff0)
                embed_catch.set_footer(text=f"Caught by {auth.name}#{auth.discriminator}", icon_url=auth.avatar_url_as(format="png", size=128))
                interval = random.uniform(5, 9)       
                await cur.callproc('GIVE_CREDITS', (state.message.author.id, price))
            await conn.commit()
        await asyncio.sleep(interval)
        await cast_msg.delete()
        await state.message.channel.send(embed=embed_catch)

    async def shop(self, state, args):
        # display all list items

        # introduce an async while loop which delivers the desired item list until the user quits the store

        # on purchase, modify the user's loadout/stats
        pass

    async def trap(self, host, state, args):
        auth = state.message.author
        chan = state.message.channel
        trap = self.trap_list.get(auth.id, False)

        if trap:
            if trap.isclaimed:
                await state.message.channel.send(f"Your trap at {self.LOC_PRINT[trap.location]} was claimed...")
                self.trap_list.pop(auth.id)
                trap = None
            else:
                # unclaimed active trap
                descrip = f"**Time active:**\n{host.format_duration(time.time() - trap.start_time)}\n**Time before public:**\n{host.format_duration(trap.duration - (time.time() - trap.start_time))}\n\n***Would you like to fetch it now?***"
                trap_info = Embed(title=f"Your trap at {self.LOC_PRINT[trap.location]}", description=descrip, color=0xa0fff0)
                reaclist = ['\U00002714', '\U0000274c']
                if state.message.guild.id != trap.server:
                    trap_info.set_footer(text="From a faraway land...")
                try:
                    answer = await host.add_reactions(chan, trap_info, char_list=reaclist, author=auth)
                except MessageDeletedException:
                    return
                if answer == 0:
                    result_embed = trap.catch(auth)
                    await chan.send(embed=result_embed)
                else:
                    await chan.send("*Your trap sinks back into the water...*")
                pass

        # no traps active
        else:
            descrip = ""
            serverlist = self.server_traps.get(state.message.guild.id, False)
            reaclist = ['\U0000274c', '\U0001f4e6']
            if serverlist and len(serverlist) > 0:
                descrip += f"There are {len(serverlist)} unclaimed traps in this server. Use \U0001f3a3 to try for one!\n"
                reaclist.append('\U0001f3a3')
            else:
                descrip += "No unclaimed traps available, for now...\n"
            trap_embed = Embed(title="Fishing Traps", description=descrip, color=0xa0fff0)
            try:
                answer = await host.add_reactions(chan, trap_embed, char_list=reaclist, author=auth)
            except MessageDeletedException:
                return  # bleck

            if answer == 0:
                await chan.send("*No fish for today...*")
                return
            elif answer == 1:
                try:
                    locindex = await self.pick_location(host, auth, state.message.channel, 6)  # TODO: account for prices
                except MessageDeletedException:
                    return
                if locindex == -1:
                    await state.message.channel.send("`Fishing cancelled -- response not sent in time.`")
                    return
                # create trap here
                trap = Trap(locindex, time.time(), 86400, auth, state.message.guild.id, self, host)
                self.trap_list[auth.id] = trap
                await state.message.channel.send("*Trap set for 24 hours from now. Make sure to check in before then!*")
            elif answer == 2:
                # attempt to steal the first trap in the list.
                # if successful, pop it off
                pass

        


def cdf_normal(z):
    # from python docs: https://docs.python.org/3/library/math.html
    return (1.0 + math.erf(z / math.sqrt(2))) / 2
