from .base import Module, Command
from discord import Embed
import json
import datetime
import random


class NSFW(Module):
    async def handle_message(self, state):
        if state.command_host == self:
            if not state.message.channel.nsfw:
                await state.message.channel.send(f'```Command "{state.args[0]}" for NSFW channels only!```')
            else:
                await self.command_list[state.args[0]](self.host, state)

    # TODO:
    #   - implement per (user, guild, ...) cooldowns (DB?)
    #       - discord py tracks cooldowns in a massive key/val structure that processes IDs and simply returns whether or not they are on cooldown
    #       - each ID is unique and so based on some information from the relevant cooldown we can figure out whether or not the function should be called
    #       - no idea if performance will become an issue but we can find out :)
    #       - realistically people aren't spamming all functions in all servers at all times (and if they are i will veto them)
    #       - so keeping track of (high ceiling max) a few thousand cooldown objects at a time should not be a big deal.
    #       - last argument page{n}
    #       - add consistent command flagger (-, --, +)
    @Command.register(name="e621")
    async def esix(host, state):
        # check if the command is it
        state.args.pop(0)
        pagenum = None
        # check if its just a command and no tags
        if len(state.args) >= 1 and state.args[-1].startswith("page"):
            pagenum = state.args.pop(-1)
            try:
                pagenum = int(pagenum[4:])
            except:
                await state.message.channel.send("Invalid page number. Defaulting to page 1.")
                pagenum = None
        tagstring = ("+".join(state.args))
        if pagenum is not None:
            tagstring += "&page=" + str(pagenum)
        response_message = await state.message.channel.send("```Searching...```")
        await state.message.channel.trigger_typing()
        url = f"https://e621.net/post/index.json?limit=50&tags={tagstring}"
        resp = await Module._http_get_request(url)
        status = resp["status"]
        await response_message.delete()
        if (status >= 200 and status < 300):
            parsed_json = json.loads(resp["text"])
            if len(parsed_json) == 0:
                await state.message.channel.send("No results found for that query.")
            else:
                target = random.choice(parsed_json)
                url = target['sample_url']
                # todo: add
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
                response_embed = Embed(title="E621",
                                       type="rich",
                                       colour=0x00549D,
                                       description=description,
                                       url="https://e621.net")
                response_embed.set_image(url=url)
                response_embed.set_author(name=host.user.name, icon_url=host.user.avatar_url_as(format="png", size=64))
                await state.message.channel.send(embed=response_embed)
                # await state.message.channel.send(random.choice(parsed_json)['file_url'])
        else:
            await state.message.channel.send("Error {resp['status']}: resp['text']")
        # thanks stack: https://stackoverflow.com/questions/25231989/how-to-check-if-a-variable-is-a-dictionary-in-python
        # worry about edge cases in a sec
