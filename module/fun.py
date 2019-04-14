from .base import Module, Command
from discord import Status, Embed
import random
import math
import json
import datetime

'''
aiohttp:
    asynch http requests in line with what we would expect
    get it ready!
'''


class Fun(Module):
    @Command.register(name="coinflip", descrip="flip a coin!")
    async def coinflip(host, state):
        flip = random.random()
        if flip < 0.02:
            randuser = None
            while True:
                randuser = random.choice(state.message.guild.members)
                if randuser.status == Status.online:
                    break
            randuser = randuser.id
            await state.message.channel.send(random.choice((
                "The coin landed on its side!",
                "The coin penetrated the floor and shattered.",
                "The coin vanished instantly...",
                f"The coin struck <@{randuser}> in the head!",
                "father says to quiet down",
                "Sadly, your coin was thefted by a passerby.",
                f"<@{randuser}> stole the coin in a stunning display of dexterity!",
                "please stop asking me to flip coins"
            )))
        elif flip < 0.51:
            await state.message.channel.send("You flipped heads!")
        else:
            await state.message.channel.send("You flipped tails!")
        print("ass")

    @Command.register(name="pushup")
    async def pushup(host, state):
        count = int(math.floor(float(state.args[1]) + 1))
        await state.message.channel.send(f"that's cool but i can do {count} pushups")

    # TODO:
    #   - create a module for NSFW commands
    #   - deal with exceptions
    @Command.register(name="e621")
    async def esix(host, state):
        # pop off the command, the rest is tags
        state.args.pop(0)
        tagstring = ("+".join(state.args))
        url = f"https://e621.net/post/index.json?limit=20&tags={tagstring}"
        resp = await Module.http_get_request(url)
        status = resp["status"]
        if (status >= 200 and status < 300):
            parsed_json = json.loads(resp["text"])
            if len(parsed_json) == 0:
                await state.message.channel.send("No results found for that query.")
            else:
                target = random.choice(parsed_json)
                url = target['sample_url']
                if url.endswith(".swf"):
                    url = target['preview_url']
                postdate = datetime.date.fromtimestamp(target['created_at']['s'])
                postdate = postdate.strftime("%B %d, %Y")
                artist = ', '.join(target['artist'])
                desc = target['description']
                if len(desc) > 200:
                    desc = desc[:200] + "..."
                elif len(desc) == 0:
                    desc = "No description available."
                description = f"*by {artist}*\n*posted {postdate}*\n\n**Score:** {target['score']}\n\n**Source (hosted on e621):** {target['file_url']}\n\n*{desc}*"
                print(url)
                # this will probably get redundant, come up with a way to stylin it
                response = Embed(title="E621",
                                 type="rich",
                                 colour=0x00549D,
                                 description=description,
                                 url="https://e621.net")
                response.set_image(url=url)
                response.set_author(name=host.user.name, icon_url=host.user.avatar_url_as(format="png", size=64))
                await state.message.channel.send(embed=response)
                # await state.message.channel.send(random.choice(parsed_json)['file_url'])
        else:
            await state.message.channel.send("Error {resp['status']}: resp['text']")
        # thanks stack: https://stackoverflow.com/questions/25231989/how-to-check-if-a-variable-is-a-dictionary-in-python
        # worry about edge cases in a sec
