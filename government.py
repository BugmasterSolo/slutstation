from discord import Client
# commands will be parsed with spaces


class Government(Client):

    # parsing through modules to interpret commands:
    # each module has a set of functions that are defined in order
    # each module contains a designating "function-list" structure
    # which contains function objects
    # function objects contain info on each function, and
    # thus can be used to do anything
    # relating to the function (times called, help, etc).

    # the wrapper picks up a function and turns it into an object,
    # the wrapper is a function of the class and adds it to the class's list.
    # thus, functionality can be tacked onto commands as necessary.

    # modules can be easily loaded and unloaded by
    # implementing a template module class
    # the template contains a few necessary wrapper functions
    # modules have permissions, internal constants, log addresses and so on
    # depending on what is necessitated,
    # but the idea is that they just have to be written from scratch
    def __init__(self, prefix):
        ''''''
        # append space when referring to the bot commands
        super().__init__()
        self.prefix = prefix
        self.owner = 186944167308427264
        print("Up and running!")
        print(dir(self))

    # take care of some file imports
    # the wrapper replaces the function:
    # double check the discord py and see what it is doing exactly
    async def on_message(self, message):
        if message.author != self.user:
            # prior: if any functions might mention the bot, create
            #        a distinct class just for them, that can be achecked here.
            #        (class UserAntics)

            # deal with the case in which the bot is mentioned.
            if (self.check_if_mentioned(list=message.mentions,
                                        id=self.user.id)):
                print("that's me!")
                # this can definitely be handled by a module.
                await self.mentioned(message)
        # if the bot is not mentioned, check if the command prefix is set.
        # if so, start delegating the command to each class (async)
        # note: python supports parallelism, we could easily perform
        # a task search in parallel, or at least come up with some better
        # way to delegate tasks to given cores.

        # remove the prefix

    # the class takes care of any instances in which the bot is mentioned.
    def check_if_mentioned(self, list, id):
        return any(m.id == id for m in list)

    async def mentioned(self, message):
        lowerstring = message.content.lower()
        if "hello" in lowerstring:
            await message.channel.send(f"hello, <@{message.author.id}>!")
        else:
            await message.channel.send(f"what's up, <@{message.author.id}>!")






def load_token():
    with open("secret_token.txt", "r") as f:
        return f.read().strip()


client = Government("g")
client.run(load_token())
