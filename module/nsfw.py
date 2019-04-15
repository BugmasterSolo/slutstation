from .base import Module, Command
from discord import Embed
import json
import datetime
import random


class NSFW(Module):
    async def check(self, state):
        if state.args and state.args[0] in self.command_list:
            if not state.message.channel.nsfw:
                await state.message.channel.send(f'```Command "{state.args[0]}" for NSFW channels only!```')
                return False
            return state.args[0] in self.command_list

    # TODO:
    #   - implement per (user, guild, ...) cooldowns (DB?)
    #       - discord py tracks cooldowns in a massive key/val structure that processes IDs and simply returns whether or not they are on cooldown
    #       - each ID is unique and so based on some information from the relevant cooldown we can figure out whether or not the function should be called
    #       - no idea if performance will become an issue but we can find out :)
    #       - realistically people aren't spamming all functions in all servers at all times (and if they are i will veto them)
    #       - so keeping track of (high ceiling max) a few thousand cooldown objects at a time should not be a big deal.
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
