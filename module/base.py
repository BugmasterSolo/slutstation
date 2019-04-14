# todo: ENUM for describing what information modules are looking for
# for inst: a module might read all messages for a leveling system.

import asyncio
import aiohttp
# we're doing it all from scratch baby

# template for future modules.

# defines a function container with function similar to discord.py's cogs,
# built from scratch in pursuit of some additional functionality that may/may not
# prove useful. whatever, it's for fun :-)


# todo:
# means of modules broadcasting their functional needs
'''
with in python:
    classes will have an __enter__ and __exit__ function which takes care of cleanup
    xhr requests work great for this since they're destroyed once used

    with A() as a, B() as b
    ===
    with A() as a:
        with B() as b:
'''


class Module:
    '''A module is a component of the bot which contains a series of functions.

    By extending the module and adding functions with the @Command decorator,
    a module can be given a set of functions, generally with similar traits.

    Modules are designed around similar functionality, and will only run if the inputted information
    matches those criteria.

    This pretty much mimicks the "discord.ext.commands.Cog" functionality,
    or at least that is the goal.
    '''
    # getting the event loop inside of the module and passing it to all of the functions.
    def __init__(self, host, *args, **kwargs):
        self.command_list = {}
        self.host = host
        for func in dir(self):
            f = getattr(self, func)
            if isinstance(f, Command):
                for alias in f.alias:
                    # this check is fine-- convert to set for massive checks.
                    if alias in self.command_list.keys():
                        raise AttributeError(f"\nDuplicate command {alias} found in module. Please double check your function names.")
                    self.command_list[alias] = f
        # created list of commands -- check for any issues.
        print("List of commands: ")
        # create dict of aliases and functions. (duh!)
        print(self.command_list)

    # dict simplifies this considerably
    async def get_command(self, cmd):
        '''
        Returns the relevant Command if available, otherwise returns none.
        '''
        for i in self.command_list.keys():
            if i == cmd:
                return self.command_list[i]
        pass

    async def check(self, state):
        '''
        Modules are designed to respond to a wide range of inputs, but responding to all messages
        takes time. The check method aims to alleviate extra processing whenever possible.

        The check method is a first pass, notifying the bot as to whether the content of the Message
        is worth interpreting, or whether it can ignore the contents and save some time.

        For instance, one module may ask to read the contents of all Messages, for the purpose of logging
        user activity (level up system, NSA plant). In this event, the check function might always return
        True, notifying the bot that the module needs to examine the message contents further.

        On the other hand, a module designed for administrative purposes might want to check if the message
        came from a server admin, and only return True if the message is from a server administrator
        (perhaps reading back a canned "administrator only!" message if the function contains a prefix--
        either way, this saves time, as the bot does not need to check all listed commands and aliases)

        The default assumes that the bot needs to read the contents of all messages-- you are encouraged
        to overwrite this! It will save some compute time and it will make the bot smile at you :)
        '''
        if state.args:
            return state.args[0] in self.command_list

    async def handle_message(self, state):
        '''
        Handles user input that passes the initial check.
        Defaults to checking the command list and passing the context to the command.
        '''
        if state.command_host == self:
            await self.command_list[state.args[0]](self.host, state)

    # mimicking promises :-)
    # i think futures should cover this as well
    # add coros and shit and doll this up a bunch
    async def http_get_request(domain):
        # some of the requests were failing wo this.
        async with aiohttp.ClientSession(headers={"user-agent":
                                                  "Government(Discord.py) / 0.01 -- https://github.com/jamieboy1337/slutstation; sorry im just lerning :-)"
                                                  }) as session:
            print(domain)
            async with session.get(domain) as resp:
                text = await resp.text()
                return {
                    "status": resp.status,
                    "text": text
                }


# decorator class for funky functions
# self is redefined, and thus will not work.
class Command:
    '''Commands make up the bulk of each module, referring to a function of the bot.

        Commands accept the following initial parameters:

        coro: The function attached to the command. This runs every time the command is called,
              via the object's __call__ function.

              Throws a TypeError if the function is not a coroutine (asynchronous)

        name (opt): The name attached to the command -- the primary means of calling the function.
                    Throws an AttributeError if the name is already present.
                    Defaults to the function name.

        descrip (opt): The description attached to the command. Referenced when the user calls the built
                       in help function (TODO: build in the help function, w embed)

                       Defaults to a simple blanket statement.

        alias (opt): Alternative commands used to call a command.
                     Name is automatically added to the list of aliases.

            Commands must accept two parameters:
                - host, referring to the bot.
                - message, referring to the passed message.
    '''
    def __init__(self, func, **kwargs):
        self.name = kwargs.get("name", func.__name__)
        # check if coroutine
        if not asyncio.iscoroutinefunction(func):
            raise TypeError("Command is not a coroutine. Add async to the function header, maybe rework a few things.")
        self.func = func
        self.descrip = kwargs.get("descrip", func.__doc__ or "No description available.")
        self.alias = [kwargs.get("name", func.__name__)]
        # fix please
        if not kwargs.get("alias") is None:
            self.alias.append(kwargs.get("alias"))

    async def __call__(self, host, message, *args, **kwargs):
        await self.func(host, message, *args, **kwargs)

    def register(func=None, *args, **kwargs):
        '''
        Decorator used to instantiate command objects from functions.

        @Command.register[(options)]
        def bot_command(...):
            ...

        For descriptions of options view the Command docstring.
        '''
        if func:
            return Command(func)

        def wrapper(func):
            return Command(func, *args, **kwargs)
        return wrapper
