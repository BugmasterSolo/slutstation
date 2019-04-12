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
    def __init__(self, host, *args, **kwargs):
        self.function_list = []
        self.host = host
        for func in dir(self):
            if isinstance(self.func, Command):
                for a in func.alias:
                    if any(a in c.alias for c in self.function_list):
                        raise AttributeError(f"Duplicate command {a} found in function {func.name}")
                self.function_list.append(func)
        # created list of commands -- check for any issues.

    def check_function_list(self, command, *args, **kwargs):
        for command in self.command_list:
            if command.name == command or any(a == command for a in command.alias):
                return command
        return None


# decorator
class Command:
    def __init__(self, coro, **kwargs):
        self.name = kwargs.get("name", coro.__name__)
        # check if coroutine
        self.coro = coro
        self.descrip = kwargs.get("descrip", coro.__doc__ or "No description available.")
        # add check for redundant parameters, defaults
        self.alias = kwargs.get("name", coro.__name__)
        if not kwargs.get("alias") is None:
            # this sucks
            self.alias.append(kwargs.get("alias"))

    # i hope this works right
    async def __call__(self, *args, **kwargs):
        print(f"Command {self.name} called.")
        # please
        self.coro(*args, **kwargs)
