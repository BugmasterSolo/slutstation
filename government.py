from discord import Client


class Government(Client):

    def __init__(self, prefix):
        # append space when referring to the bot commands
        super().__init__()
        self.prefix = prefix

    # take care of some file imports
    async def on_message(self, message):
        if message.author != self.user:
            # implement some sort of command loop for parsing inputs
            if (self.check_if_contains(list=message.mentions, term=self.user.id)):
                print("that's me!")
                await self.mentioned(message)

    def check_if_contains(self, list, term):
        for m in list:
            if (m.id == term):
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
