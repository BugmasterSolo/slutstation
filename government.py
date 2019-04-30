# todo: modules build their help strings on init. strings are passed to the bot object, and the bot splices them together.
#       thus, it's very easy to separate things out by module.
# yield: generator (pauses on yield, can be picked back up)

import asyncio

from discord import Client, Game
import module
import time
import json
import aiomysql as sql
# import all modules, construct them in the bot code
# commands will be parsed with spaces
# todo: fast dict traversal for double checking long lists!
# additionally: local/remote storage of vars based on associated delay!


# lol
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
        self.uptime = time.time()
        self.prefix = prefix
        self.owner = 186944167308427264
        print("Up and running!")
        self.module_list = []
        self.loop = asyncio.get_event_loop()
        self.db = None
        self.cur = None
        self.loop.run_until_complete(self.import_all())
        self.loop.run_until_complete(self.create_db())
        self.unique_commands = {}
        for mod in self.module_list:
            for command in mod.command_list:
                if command in self.unique_commands:
                    raise ValueError(f"Duplicate commands: {command} in {mod.__name__} and {self.unique_commands[command].__name__}")
                self.unique_commands[command] = mod

    async def create_db(self):
        sql_cred_array = None
        with open("db_token.json", "r") as f:
            sql_cred_array = json.loads(f.read().strip())
        self.db = await sql.create_pool(loop=self.loop, **sql_cred_array)

    async def on_ready(self):
        await self.change_presence(activity=Game(name="mike craft"))

    async def on_message(self, message):
        if message.author.id != self.user.id:
            trimmed_message = message.content
            command_host = None
            command_name = None
            if (trimmed_message.startswith(self.prefix)):
                trimmed_message = trimmed_message.strip(self.prefix)
                word_cut = trimmed_message.find(" ")
                if word_cut < 0:
                    command_name = trimmed_message
                else:
                    command_name = trimmed_message[:word_cut]
                # this is dumb
                trimmed_message = trimmed_message[word_cut:].strip()
                # will default it to none + string checks for invalid input
                command_host = self.unique_commands.get(command_name, "INVALID")
            state = State(host=self, message=message, command_host=command_host, content=trimmed_message, command_name=command_name)
            for mod in self.module_list:
                if await mod.check(state):
                    await mod.handle_message(state)
                    # guaranteed that commands only belong to one
                    break

    async def import_all(self):
        await self.import_extension(module.Fun)
        await self.import_extension(module.NSFW)
        await self.import_extension(module.Steam)
        await self.import_extension(module.Stattrack)
        await self.import_extension(module.Player)

    async def import_extension(self, cls):
        try:
            self.module_list.append(cls(self))
        except Exception as e:
            err_string = str(e)
            print(f"Exception occurred: \n{err_string}")
            pass


def load_token():
    with open("secret_token.txt", "r") as f:
        return f.read().strip()


client = Government("g ")
client.run(load_token())
