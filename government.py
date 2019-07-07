# todo: give the bot some consistency across the board (formatting guidelines, style, syntax, etc)
#       create the help docs and get them online
#
#
#
#
#
# WRITE UP SOME EDITING GUIDELINES AND MODIFY THE CODE TO RESPECT THEM.
#
#
#
#
#

import asyncio
import sys

import discord
from discord import Client, Game
import module
import time
import json
import aiomysql as sql
import logging
import math
import re
from discord.errors import NotFound
import aiohttp


from module.base import GuildUpdateListener, MessageDeletedException

logger = logging.basicConfig(level=logging.INFO)

http_header = {
    "user-agent": "Government(Discord.py) / 0.091 -- https://github.com/jamieboy1337/slutstation; sorry im just lerning :-)"
}


class State:
    '''Wrapper for variables provided in message event, includes some added values as necessary.
        TODO: remove the need for state and move the function parsing to a hidden module var.'''
    def __init__(self, host, message, **kwargs):
        self.message = message
        self.host = host
        for arg in kwargs:
            setattr(self, arg, kwargs.get(arg, None))


class Government(Client):
    A_EMOJI = 0x0001F1E6
    QUOTE_TYPES = "\"“”'"

    def __init__(self, prefix):
        super().__init__()
        self.uptime = time.time()                           # for tracking current uptime.
        self.prefix = prefix                                # bot prefix for commands.
        self.owner = 186944167308427264                     # me
        self.logged_users = {}                              # dict of users known to exist in DB.
        self.module_list = []                               # list of all instantiated modules
        self.loop = asyncio.get_event_loop()                # current running event looped (started by discord py)
        self.db = None                           # current database connection (aiomysql pool)
        self.loop.run_until_complete(self.import_all())
        self.loop.run_until_complete(self.create_db())
        self.unique_commands = {}                           # dict of unique commands (k: command name or alias -- v: modules)

        self.guild_update_listeners = {}                    # used by music player and associated utilities to divvy out events

        # rebuild module calls to parse json
        command_info = {}
        for mod in self.module_list:
            for command in mod.command_list:  # oh duh, this gets keys and not values; carry on
                if command in self.unique_commands:
                    raise ValueError(f"Duplicate commands: {command} in {mod.__name__} and {self.unique_commands[command].__name__}")
                self.unique_commands[command] = mod  # mod value ties functions to modules
                if command_info.get(command) is None:
                    command_info[command] = {
                        "name": command,
                        "descrip": mod.command_list[command].descrip,
                        "aliases": mod.command_list[command].alias
                    }
        # oophs
        self.loop.run_until_complete(self.http_post_request("http://baboo.mobi/government/help_function.php", json.dumps(command_info)))
        print("Up and running!")

    async def create_db(self):
        sql_cred_array = None
        with open("db_token.json", "r") as f:
            sql_cred_array = json.loads(f.read().strip())
        self.db = await sql.create_pool(loop=self.loop, **sql_cred_array)  # minsize = 0?

    async def on_ready(self):
        await self.change_presence(activity=Game(name="mike craft"))

    async def on_message(self, message):
        if message.author.id != self.user.id:
            if isinstance(message.channel, discord.DMChannel):
                await message.channel.send("dont be a pussy")
                return
            await self.checkuser(message)
            trimmed_message = message.content
            command_host = None
            command_name = None
            if (trimmed_message.startswith(self.prefix)):
                trimmed_message = trimmed_message[len(self.prefix):]
                word_cut = trimmed_message.find(" ")
                if word_cut < 0:
                    command_name = trimmed_message
                else:
                    command_name = trimmed_message[:word_cut]
                if word_cut == -1:
                    trimmed_message = ""
                else:
                    trimmed_message = trimmed_message[word_cut:].strip()
                command_host = self.unique_commands.get(command_name, "INVALID")
            state = State(host=self, message=message, command_host=command_host, content=trimmed_message, command_name=command_name)
            for mod in self.module_list:
                if await mod.check(state):
                    try:
                        await mod.handle_message(state)
                    except discord.errors.Forbidden:
                        print("request in locked channel. ignoring...")

    async def on_guild_update(self, before, after):
        if self.guild_update_listeners.get(after.id):
            for listener in self.guild_update_listeners[after.id]:
                listener(before, after)

    async def add_guild_update_listener(self, listener):
        if not isinstance(listener, GuildUpdateListener):
            # raise error
            return
        if not self.guild_update_listeners.get(listener.guild.id):
            self.guild_update_listeners[listener.guild.id] = []
        self.guild_update_listeners[listener.guild.id].append(listener)
        return listener

    async def remove_guild_update_listener(self, listener):
        arr = self.guild_update_listeners[listener.guild.id]
        arr.remove(listener)
        print("deleted")
        if not arr:
            del arr

    async def import_all(self):
        await self.import_extension(module.Fun)
        await self.import_extension(module.NSFW)
        await self.import_extension(module.Steam)
        await self.import_extension(module.Stattrack)
        await self.import_extension(module.Player)
        await self.import_extension(module.ImageModule)
        await self.import_extension(module.Fishing)

    async def import_extension(self, cls):
        try:
            self.module_list.append(cls(self))
        except Exception as e:
            err_string = str(e)
            print(f"Exception occurred: \n{err_string}")
            pass

    async def checkuser(self, message):
        isLogged = self.logged_users.get(message.channel.id)
        if not isLogged:
            self.logged_users[message.channel.id] = {}
        isLogged = self.logged_users[message.channel.id].get(message.author.id)
        if not isLogged and not message.author.bot:
            async with self.db.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.callproc("USEREXISTS", (message.author.id, f"{message.author.name}#{message.author.discriminator}", message.guild.id))
                await conn.commit()
            self.logged_users[message.channel.id][message.author.id] = True  # ensures above logic passes

    def get_closing_quote(self, quote):
        # add relevant exceptions
        if quote in self.QUOTE_TYPES:
            if quote == "“":
                return "”"
            elif quote == "”":
                return "“"
            else:
                return quote

    # UTILITY FUNCTIONS BELOW!

    async def add_reactions(self, chan, embed, host, timer=0, answer_count=2, char_list=None, descrip="Get your answer in!", author=None):
        '''
Adds reactions to a desired embed, and waits for responses to come in.
In the event that the message is timed, returns the message ID to be handled appropriately.
If untimed, awaits first relevant user response and returns the index of the relevant reaction associated with it.

Required arguments:
discord.Channel chan            - The channel to which the message should be posted.
discord.Embed embed             - The intended message that will be posted.
Government host                 - The host -- used to manage the wait_for condition (of course modules have access to the host lol)

Optional arguments:
Integer timer                   - Time limit on the poll - if set to 0, waits for the user's response.
Integer answer_count            - The number of answers to be provided
Iterable char_list              - If provided, iterates over the list when listing emojis.
String descrip                  - Text tied to the description.
discord.User author             - The user that posted the relevant request.
        '''
        poll = await chan.send(embed=embed)
        # specifics!
        if char_list:
            for emote in char_list:
                await poll.add_reaction(emote)
        else:
            for i in range(answer_count):
                await poll.add_reaction(chr(self.A_EMOJI + i))
        # use wait_for to record deletion and back out of here if it occurs
        # create an async event which tracks deletion status
        # on passing delete, flip the event
        # perform a check on each stop to see if the event is flipped
        # if it is, throw an exception to be handled silently by the relevant function.
        descrip = descrip + f"\n\n{poll.jump_url}"
        if timer >= 3600:
            await asyncio.sleep(timer - 1800)
            if not await self.message_exists(chan, poll.id):
                raise MessageDeletedException()
            warning = await chan.send(f"***30 minutes remaining:\n{descrip}***")
            await asyncio.sleep(600)
            await warning.delete()
            timer = 1200
        if timer >= 900:
            await asyncio.sleep(timer - 600)
            if not await self.message_exists(chan, poll.id):
                raise MessageDeletedException()
            warning = await chan.send(f"***10 minutes remaining:\n{descrip}***")
            await asyncio.sleep(240)
            await warning.delete()
            timer = 360
        if timer >= 300:
            await asyncio.sleep(timer - 180)
            if not await self.message_exists(chan, poll.id):
                raise MessageDeletedException()
            warning = await chan.send("***3 minutes remaining!\n{descrip}***")
            await asyncio.sleep(45)
            await warning.delete()
            timer = 135
        if timer >= 120:
            await asyncio.sleep(timer - 60)
            if not await self.message_exists(chan, poll.id):
                raise MessageDeletedException()
            warning = await chan.send("***1 minute remaining!\n{descrip}***")
            await asyncio.sleep(30)
            await warning.delete()
            timer = 30
        if timer > 10:
            await asyncio.sleep(timer - 10)
            if not await self.message_exists(chan, poll.id):
                raise MessageDeletedException()
            # use a description on longer waits
            warning = await chan.send("***10 seconds remaining!***")
            await asyncio.sleep(5)
            await warning.delete()
            await asyncio.sleep(5)
        elif timer != 0:
            await asyncio.sleep(timer)
        else:  # timer = 0 means that we're waiting for a response.
            if char_list:
                def check(reaction, user):
                    return (True if author is None else user == author) and reaction.message.id == poll.id and not reaction.custom_emoji and reaction.emoji in char_list
                pass
            else:
                def check(reaction, user):
                    return (True if author is None else user == author) and reaction.message.id == poll.id and not reaction.custom_emoji and (ord(reaction.emoji) - self.A_EMOJI) < answer_count
            try:
                react = await host.wait_for("reaction_add", check=check, timeout=30)  # perform something on timeout (should handle deletion)
                await poll.delete()
                if char_list:
                    return char_list.index(react[0].emoji)
                else:
                    return ord(react[0].emoji) - self.A_EMOJI
            except asyncio.TimeoutError:
                await poll.delete()
                return -1  # indicating no response
                # user took too long
        if not await self.message_exists(chan, poll.id):
            raise MessageDeletedException()
        return poll.id
        # jump back into loop

    def format_duration(self, timer):
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

    def split(self, message):
        args = re.split(" +", message)
        if len(args) == 1 and args[0] == '':  # boo piss
            args.pop()
        return args

    async def message_exists(self, chan, id):
        try:
            await chan.fetch_message(id)  # probably a better way to do this with listener
        except NotFound:
            return False
        return True

    async def http_get_request(self, domain):  # todo: deal with exceptions cleanly
        async with aiohttp.ClientSession(headers=http_header) as session:
            print("get: " + domain)
            async with session.get(domain) as resp:
                text = await resp.text()
                return {
                    "status": resp.status,
                    "text": text
                }

    async def http_post_request(self, domain, payload):
        async with aiohttp.ClientSession(headers=http_header) as session:
            print("post: " + domain)
            async with session.post(domain, data=payload) as resp:
                text = await resp.text()
                return {
                    "status": resp.status,
                    "text": text
                }


def load_token():
    if (len(sys.argv) > 1):
        filename = "secret_token_prim.txt"
        print("running on primary")
    else:
        filename = "secret_token.txt"
        print("running on test")
    with open(filename, "r") as f:
        return f.read().strip()


if __name__ == '__main__':
    client = Government("g ")
    client.run(load_token())
