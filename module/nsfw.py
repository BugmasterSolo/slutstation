from .base import Module, Command, Scope
from discord import Embed
import json
import datetime
import random
import xml.etree.ElementTree as ET
# todo : move from datetime to time


class NSFW(Module):
    async def handle_message(self, state):
        if state.command_host == self:
            if not state.message.channel.nsfw:
                await state.message.channel.send(f'```Command "{state.args[0]}" for NSFW channels only!```')
            else:
                await self.command_list[state.args[0]](self.host, state)

    # TODO:
    #   - implement per (user, guild, ...) cooldowns (DB?)
    #       - add bantags (please, per-server)
    @Command.cooldown(scope=Scope.CHANNEL, time=5)
    @Command.register(name="e621")
    async def esix(host, state):
        # check if the command is it
        chan = state.message.channel
        tag_array, pagenum = await NSFW._parse_tags(state.args, chan)
        tagstring = ("+".join(tag_array))
        if pagenum is not None:
            tagstring += "&page=" + str(pagenum)
        response_message = await chan.send("```Searching...```")
        await chan.trigger_typing()
        url = f"https://e621.net/post/index.json?limit=50&tags={tagstring}"
        resp = await Module._http_get_request(url)
        status = resp["status"]
        parsed_json = json.loads(resp["text"])
        await response_message.delete()
        if (status >= 200 and status < 300):
            if len(parsed_json) == 0:
                await chan.send("No results found for that query.")
                # errors in request will throw a wonky status code
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
                                       url=url)
                response_embed.set_image(url=url)
                response_embed.set_author(name="E621.NET")
                await chan.send(embed=response_embed)
                # await state.message.channel.send(random.choice(parsed_json)['file_url'])
        else:
            await chan.send("Sorry, no dice: " + parsed_json['reason'])
        # thanks stack: https://stackoverflow.com/questions/25231989/how-to-check-if-a-variable-is-a-dictionary-in-python
        # worry about edge cases in a sec

    async def _parse_tags(tag_array, chan):
        tag_array.pop(0)
        pagenum = None
        if len(tag_array) >= 1 and tag_array[-1].startswith("page"):
            pagenum = tag_array.pop(-1)
            try:
                pagenum = int(pagenum[4:])
            except Exception as e:
                if isinstance(e, ValueError):
                    await chan.send("Invalid page number. Defaulting to page 1.")
                else:
                    await chan.send("An unknown error occurred. Hopefully nothing else breaks :)")
                pagenum = None
        return [tag_array, pagenum]

    @Command.cooldown(scope=Scope.CHANNEL, time=5)
    @Command.register(name="rule34")
    async def rule34(host, state):
        chan = state.message.channel
        tag_array, pagenum = await NSFW._parse_tags(state.args, chan)
        tagstring = "+".join(tag_array)
        url = f"https://rule34.xxx/index.php?page=dapi&s=post&q=index&limit=50&tags={tagstring}"
        if pagenum is not None:
            url += f"&pid={pagenum}"
        response_message = await chan.send("```Searching...```")
        await chan.trigger_typing()
        resp = await Module._http_get_request(url)
        status = resp['status']
        await response_message.delete()
        if status >= 200 and status < 300:
            target = ET.fromstring(resp['text'])
            if target.attrib['count'] == "0":
                await chan.send("No results found for that query.")
            else:
                target = random.choice(target).attrib
                source = target.get("source") or target.get("file_url")
                timestring = datetime.datetime.strptime(target['created_at'], "%a %b %d %H:%M:%S %z %Y").strftime("%B %d, %Y")
                descrip = f"*posted {timestring}*\n\n**Score: {target['score']}**\n\n**Source:**\n{source}"
                response_embed = Embed(url=source, type="rich",
                                       description=descrip, title="Rule34", color=0xa0e080)
                response_embed.set_image(url=target.get("file_url"))
                response_embed.set_author(name="RULE34.XXX")
                await chan.send(embed=response_embed)
