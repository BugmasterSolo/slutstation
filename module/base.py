# todo: ENUM for describing what information modules are looking for
# for inst: a module might read all messages for a leveling system.

import asyncio

# we're doing it all from scratch baby

# template for future modules.

# defines a function container with function similar to discord.py's cogs,
# built from scratch in pursuit of some additional functionality that may/may not
# prove useful. whatever, it's for fun :-)


class Module:
    '''A module is a component of the bot which contains a series of functions.

    By extending the module and adding functions with the @Command decorator,
    a module can be given a set of functions, generally with similar traits.

    This pretty much mimicks the "discord.ext.commands.Cog" functionality,
    or at least that is the goal.
    '''
    # getting the event loop inside of the module and passing it to all of the functions.
    def __init__(self, host, *args, **kwargs):
        self.function_list = []
        self.host = host
        for func in dir(self):
            f = getattr(self, func)
            if isinstance(getattr(self, func), Command):
                for a in f.alias:
                    if any(a in self.__getattribute__(c).alias for c in self.function_list):
                        raise AttributeError(f"\nDuplicate command {func} found in module. Please double check your function names.")
                self.function_list.append(func)
        # created list of commands -- check for any issues.
        print(self.function_list)

    async def get_command(self, command):
        '''
        Returns the relevant Command if available, otherwise returns none.
        '''
        for c in self.function_list:
            command_object = self.__getattribute__(c)
            print(command_object.alias)
            print(command)
            if any(a == command for a in command_object.alias):
                print(f"found: {command_object.name}")
                return c
        return None
# todo: generic "command not found" formatting


# decorator class for funky functions
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
        self.loop = asyncio.get_event_loop()  # for call method (sync by default)

    def __call__(self, *args, **kwargs):
        self.loop.run_until_complete(self.func(*args, *kwargs))

    def register(func=None, *args, **kwargs):
        if func:
            return Command(func)

        def wrapper(func):
            return Command(func, *args, **kwargs)
        return wrapper
