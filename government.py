from discord import Client


class Government(Client):

    def __init__(self, prefix):
        # append space when referring to the bot commands
        super().__init__()
        self.prefix = prefix
        print("Up and running!")

    # take care of some file imports
    async def on_message(self, message):
        if message.author != self.user:
            # prior: if any functions might mention the bot, create
            #        a distinct class just for them, that can be achecked here.
            #        (class UserAntics)

            # deal with the case in which the bot is mentioned.
            if (self.check_if_mentioned(list=message.mentions,
                                        id=self.user.id)):
                print("that's me!")
                await self.mentioned(message)
        # if the bot is not mentioned, check if the command prefix is set.
        # if so, start delegating the command to each class (async)
        # note: python supports parallelism, we could easily perform
        # a task search in parallel, or at least come up with some better
        # way to delegate tasks to given cores.

    # the class takes care of any instances in which the bot is mentioned.
    def check_if_mentioned(self, list, id):
        for m in list:
            if (m.id == id):
                return True
        return False

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
