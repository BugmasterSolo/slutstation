# todo: modules build their help strings on init. strings are passed to the bot object, and the bot splices them together.
#       thus, it's very easy to separate things out by module.

import re
import asyncio

from discord import Client, Game
import module
import time
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
        # dynamically import available modules and add them to internals
        # append space when referring to the bot commands
        super().__init__()
        self.uptime = time.time()
        self.prefix = prefix
        self.owner = 186944167308427264  # hello :)  used if the bot needs to do anything executive :)
        print("Up and running!")
        self.module_list = []
        self.loop = asyncio.get_event_loop()
        self.loop.run_until_complete(self.import_all())
        # ensuring commands don't overlap.
        self.unique_commands = {}
        for mod in self.module_list:
            for command in mod.command_list:
                if command in self.unique_commands:
                    raise ValueError(f"Duplicate commands: {command} in {mod.__name__} and {self.unique_commands[command].__name__}")
                # this might be pointless, if not implement it,
                # it'll save some guts
                self.unique_commands[command] = mod

    # rework parsing of commands. the bot should only respond to mentions
    # if they do not involve a command.

    async def on_ready(self):
        await self.change_presence(activity=Game(name="mike craft"))

    # incorporate everything into the "message.author != self.user" check
    async def on_message(self, message):
        if message.author.id != self.user.id:
            trimmed_message = message.content
            # instantiate args-- if args = none: no prefix.
            args = None
            command_host = None
            if (trimmed_message.startswith(self.prefix)):
                trimmed_message = trimmed_message.strip(self.prefix)
                args = re.split(" +", trimmed_message)
                if args[0] in self.unique_commands:
                    # TODO: eliminate unique_commands, it's unwieldy and can be eliminated
                    command_host = self.unique_commands[args[0]]
            state = State(self, message, args=args, command_host=command_host)
            for mod in self.module_list:
                if await mod.check(state):
                    await mod.handle_message(state)
                    # guaranteed that commands only belong to one
                    break

    # g :)
    async def import_all(self):
        await self.import_extension(module.Fun)
        await self.import_extension(module.NSFW)
        await self.import_extension(module.Steam)

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


'''
Takeaway: the function wrapper will return the object we want!
When arguments are passed: The wrapper performs func = wrapper(args)(func). This produces the desired result!

'''
client = Government("g ")
client.run(load_token())
