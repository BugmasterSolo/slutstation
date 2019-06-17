# todo: ENUM for describing what information modules are looking for
# for inst: a module might read all messages for a leveling system.

import asyncio
import aiohttp
import time
import math
import re
from enum import Enum
import traceback
# we're doing it all from scratch baby

# todo: move functions into command object instead. makes more sense generally

# lower two bits: cooldown scope.
# upper bit: cooldown type.
class Scope(Enum):
    USER = 0        # per user
    CHANNEL = 1     # per channel
    SERVER = 2      # per server
    GLOBAL = 3      # ultra exclusive

    # cooldown time type

    RUN = 4         # ends some time after function finishes running
    TIME = 0        # ends some time after call

# template for future modules.

# defines a function container with function similar to discord.py's cogs,
# built from scratch in pursuit of some additional functionality that may/may not
# prove useful. whatever, it's for fun :-)


http_header = {
    "user-agent": "Government(Discord.py) / 0.062 -- https://github.com/jamieboy1337/slutstation; sorry im just lerning :-)"
}


# todo:
# means of modules broadcasting their functional needs
class Module:
    '''A module is a component of the bot which contains a series of functions.

    By extending the module and adding functions with the @Command decorator,
    a module can be given a set of functions, generally with similar traits.

    Modules are designed around similar functionality, and will only run if the inputted information
    matches those criteria.

    This pretty much mimicks the "discord.ext.commands.Cog" functionality,
    or at least that is the goal.
    '''

    A_EMOJI = 0x0001F1E6
    QUOTE_TYPES = "\"“”'"

    # getting the event loop inside of the module and passing it to all of the functions.
    def __init__(self, host, *args, **kwargs):
        self.command_list = {}
        self.host = host
        for func in dir(self):
            f = getattr(self, func)
            if isinstance(f, Command):
                if self.command_list.get(f.name) is not None:
                    raise AttributeError(f"\nDuplicate name {f.name} found. Please ensure that you're avoiding duplicates.")
                self.command_list[f.name] = f  # list of potential commands and the coinciding function
                for alias in f.alias:
                    # this check is fine-- convert to set for massive checks.
                    if self.command_list.get(alias) is not None:
                        raise AttributeError(f"\nDuplicate command {alias} found in module. Please double check your function names.")
                    self.command_list[alias] = f

    # dict simplifies this considerably
    async def get_command(self, cmd):
        '''
        Returns the relevant Command if available, otherwise returns none.
        '''
        return self.command_list.get(cmd)
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
        if state.command_host:
            return self == state.command_host
        return False

    async def handle_message(self, state):
        '''
        Handles user input that passes the initial check.
        Defaults to checking the command list and passing the context to the command.
        '''
        if state.command_host == self:
            await self.command_list[state.command_name](self.host, state)  # TODO: get rid of host in all cases, since it's included in "state"

    async def _http_get_request(domain):  # todo: deal with exceptions cleanly
        async with aiohttp.ClientSession(headers=http_header) as session:
            print("get: " + domain)
            async with session.get(domain) as resp:
                text = await resp.text()
                return {
                    "status": resp.status,
                    "text": text
                }

    async def _http_post_request(domain, payload):
        async with aiohttp.ClientSession(headers=http_header) as session:
            print("post: " + domain)
            async with session.post(domain, data=payload) as resp:
                text = await resp.text()
                return {
                    "status": resp.status,
                    "text": text
                }

    def get_closing_quote(quote):
        # add relevant exceptions
        if quote in Module.QUOTE_TYPES:
            if quote == "“":
                return "”"
            elif quote == "”":
                return "“"
            else:
                return quote


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
        # command_host could just as easily be passed here
        self.name = kwargs.get("name", func.__name__)
        # check if coroutine
        if not asyncio.iscoroutinefunction(func):
            raise TypeError("Command is not a coroutine. Add async to the function header, maybe rework a few things.")
        self.func = func
        self.descrip = kwargs.get("descrip", func.__doc__ or "No description available.")
        self.alias = []
        self.cooldown = None
        # safe to set
        self.cooltime = None
        self.cooldown_array = {}
        # fix please
        if not kwargs.get("alias") is None:
            self.alias.append(kwargs.get("alias"))

    async def __call__(self, host, state, *args, **kwargs):
        try:
            uid = self._get_cooldown_id(state.message)
            if not uid == 0:
                cur_time = time.time()
                call_time = self.cooldown_array.get(uid)
                if call_time is None:
                    # poppin
                    if self.cooldown >= 4:
                        cur_time = cur_time * -1
                    self.cooldown_array[uid] = cur_time
                else:
                    time_diff = cur_time - call_time
                    if time_diff > self.cooltime and call_time > 0:
                        if self.cooldown >= 4:
                            cur_time = cur_time * -1
                        self.cooldown_array[uid] = cur_time
                    else:
                        chan = state.message.channel
                        if call_time < 0:
                            warn = await chan.send("*please be patient i am trying my hardest already*")
                            await asyncio.sleep(3)
                            await warn.delete()
                        else:
                            await state.message.channel.send(f"`That function is on cooldown for {self.cooltime - abs(time_diff):.2f} more seconds.`")
                        # eh
                        return
                print("called")
            await self.func(host, state, *args, **kwargs)
            if not uid == 0 and self.cooldown >= 4:
                self.cooldown_array[uid] = time.time()
        except Exception as e:
            print("Something went wrong during a command call. The following exception was thrown: ")  # still throws, should be more graceful
            print(e)
            if not uid == 0:
                self.cooldown_array[uid] = time.time()
            traceback.print_exc()

    async def add_reactions(chan, embed, host, timer=0, loop=None, char_list=None, descrip="Get your answer in!", author=None):  # not necessary always
        '''Side note: loop is for the piss.
++ TODO: rework into a module instance function (wait that doesn't work lmao fuck this shit)
Command call should implicitly pass in the host.
Adds reactions to a desired embed, and waits for responses to come in.

Required arguments:
discord.Channel chan            - The channel to which the message should be posted.
discord.Embed embed             - The intended message that will be posted.
Government host                 - The host -- used to manage the wait_for condition (of course modules have access to the host lol)
Integer timer                   - Time limit on the poll - if set to 0, waits for the user's response.
Iterable loop                   - very bad -- determines which emojis should be posted relative to the letter A.
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
            for i in loop:
                await poll.add_reaction(chr(Module.A_EMOJI + i))
        # more dynamic response
        if timer >= 3600:
            await asyncio.sleep(timer - 1800)
            warning = await chan.send(f"***30 minutes remaining: '{descrip}'***")
            await asyncio.sleep(60)
            await warning.delete()
            timer = 1740
        if timer >= 900:
            await asyncio.sleep(timer - 600)
            warning = await chan.send(f"***10 minutes remaining: '{descrip}'***")
            await asyncio.sleep(30)
            await warning.delete()
            timer = 570
        if timer >= 300:
            await asyncio.sleep(timer - 180)
            warning = await chan.send("***3 minutes remaining!***")
            await asyncio.sleep(5)
            await warning.delete()
            timer = 175
        if timer >= 120:
            await asyncio.sleep(timer - 60)
            warning = await chan.send("***1 minute remaining!***")
            await asyncio.sleep(5)
            await warning.delete()
            timer = 55
        if timer > 10:
            await asyncio.sleep(timer - 10)
            # use a description on longer waits
            warning = await chan.send("***10 seconds remaining!***")
            await asyncio.sleep(5)
            await warning.delete()
            await asyncio.sleep(5)
        elif timer != 0:
            await asyncio.sleep(timer)
        else:  # timer = 0 means that we're waiting for a response.
            if author is None:
                print("nice one fucker")

            def check(reaction, user):
                return user == author and reaction.message == poll
            try:
                await host.wait_for("reaction_add", check=check, timeout=30)  # perform something on timeout
            except asyncio.TimeoutError:
                pass
                # user took too long
        return poll.id
        # jump back into loop

    def format_duration(timer):
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

    def _get_cooldown_id(self, message):
        if self.cooldown is not None:
            cool = self.cooldown & 3
            if cool == 0:
                return message.author.id
            elif cool == 1:
                return message.channel.id
            elif cool == 2:
                return message.guild.id
            elif cool == 3:
                return 1
        return 0

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

    def cooldown(cmd=None, scope=Scope.CHANNEL, type=Scope.TIME, time=15):
        if cmd:
            cmd.cooldown = scope
            cmd.cooltime = time
            return cmd

        def wrapper(cmd):
            cmd.cooldown = scope.value | type.value
            cmd.cooltime = time
            return cmd

        return wrapper

    def split(message):
        args = re.split(" +", message)
        if len(args) == 1 and args[0] == '':  # boo piss
            args.pop()
        return args
        # more checks might be necessary who knows


class GuildUpdateListener:
    def __init__(self, guild, check, coro):
        self.guild = guild
        self.check = check
        self.on_guild_update = coro

    def __call__(self, before, after):
        if self.check(before, after):
            asyncio.create_task(self.on_guild_update(after))
