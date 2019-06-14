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

import discord
from discord import Client, Game
import module
import time
import json
import aiomysql as sql
import logging


from module.base import GuildUpdateListener

logger = logging.basicConfig(level=logging.INFO)


class State:
    '''Wrapper for variables provided in message event, includes some added values as necessary.
        TODO: remove the need for state and move the function parsing to a hidden module var.'''
    def __init__(self, host, message, **kwargs):
        self.message = message
        self.host = host
        for arg in kwargs:
            setattr(self, arg, kwargs.get(arg, None))


class Government(Client):
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
        self.loop.run_until_complete(module.Module._http_post_request("http://baboo.mobi/government/help_function.php", json.dumps(command_info)))
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
        if self.guild_update_listeners[after.id]:
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


def load_token():
    with open("secret_token.txt", "r") as f:
        return f.read().strip()


if __name__ == '__main__':
    client = Government("g ")
    client.run(load_token())
