import asyncio

from discord import Client
from module import Test

# import all modules, construct them in the bot code
# commands will be parsed with spaces

class Government(Client):
    def __init__(self, prefix):
        # dynamically import available modules and add them to internals
        # append space when referring to the bot commands
        super().__init__()
        self.prefix = prefix
        self.owner = 186944167308427264  # hello :)
        print("Up and running!")
        self.module_list = [];
        # place imported modules here.

    async def on_message(self, message):
        if message.author != self.user:
            if (self.check_if_mentioned(list=message.mentions,
                                        id=self.user.id)):
                print("that's me!")
                await self.mentioned(message)


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

'''def Wrap(func=None, *args, **kwargs):
    if func:
        return _Wrap(func)
    def wrapper(func):
        return _Wrap(func, *args, **kwargs)
    return wrapper

class _Wrap:
    def __init__(self, func):
        print("i have been reborn a _Wrap")
        self.func = func

    def __call__(self):
        print("i am of type _Wrap")
        self.func()

@Wrap
def test():
    print("i am of type function")


# test is now _Wrap! it passed straight through!
if isinstance(test, _Wrap):
    print("it worked!")
else:
    print("ok")

test()

'''
client = Government("g")
client.run(load_token())
