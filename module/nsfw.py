from .base import Module, Command, Scope, HTTPNotFoundException
from discord import Embed
import json
import datetime  # move to time!
import random
import xml.etree.ElementTree as ET
import cfscrape
# todo : move from datetime to time


class NSFW(Module):
    async def handle_message(self, state):
        if state.command_host == self:
            if not state.message.channel.nsfw:
                await state.message.channel.send(f'```Command "{state.command_name}" for NSFW channels only!```')
            else:
                await self.command_list[state.command_name](self.host, state)

    def check_tags(args):
        BANNED_ARGS = ("loli", "child", "shota", "cub", "kid", "pedophilia")
        overlap = [x for x in args if x in BANNED_ARGS]
        # i see you staff team
        return (len(overlap) > 0)

    # TODO:
    #       - add bantags (please, per-server)
    @Command.cooldown(scope=Scope.CHANNEL, time=5)
    @Command.register(name="e621")
    async def esix(host, state):
        '''
Grabs images from e621.net. Tags are separated by white space, all valid tags are supported.

Optional page count parameter if you're out of the good stuff. Defaults to page 1.

Usage:
g e621 [tag1 tag2 ... tag6] (page<int>)
        '''
        # check if the command is it
        chan = state.message.channel
        args = host.split(state.content)
        if NSFW.check_tags(args):
            await chan.send("https://www.youtube.com/watch?v=_YmDcCpD1gc")
            print("diddler")
            return
        tag_array, pagenum = await NSFW._parse_tags(args, chan)
        tagstring = ("+".join(tag_array))
        if pagenum is not None:
            tagstring += "&page=" + str(pagenum)
        response_message = await chan.send("```Searching...```")
        await chan.trigger_typing()
        url = f"https://e621.net/post/index.json?limit=50&tags={tagstring}"
        # cloudflare dodging hehe
        cf = cfscrape.CloudflareScraper()
        cf_resp = await host.loop.run_in_executor(executor=None, func=lambda: cf.get(url))
        resp = cf_resp.content
        status = cf_resp.status_code
        parsed_json = json.loads(resp)
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
        else:
            await chan.send("Sorry, no dice: " + parsed_json['reason'])
        # thanks stack: https://stackoverflow.com/questions/25231989/how-to-check-if-a-variable-is-a-dictionary-in-python

    async def _parse_tags(tag_array, chan):
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
        '''
Grabs images from rule34.xxx. Tags separated by white space, all valid tags are supported.

Optional pagenum parameter fetches more stuff if you're thirsting for the flesh.

Usage:
g rule34 [tag1 tag2 tag3 ... tag6] (page<int>)
        '''
        chan = state.message.channel
        args = host.split(state.content)
        if NSFW.check_tags(args):
            await chan.send("https://www.youtube.com/watch?v=C_bJyDxYGW4")
            print("diddler")
            return
        tag_array, pagenum = await NSFW._parse_tags(args, chan)
        tagstring = "+".join(tag_array)
        url = f"https://rule34.xxx/index.php?page=dapi&s=post&q=index&limit=50&tags={tagstring}"
        if pagenum is not None:
            url += f"&pid={pagenum}"
        response_message = await chan.send("```Searching...```")
        await chan.trigger_typing()
        try:
            resp = await host.http_get_request(url)
        except HTTPNotFoundException:
            await chan.send("Request failed to return properly.")
            return
        status = resp['status']
        await response_message.delete()
        if status >= 200 and status < 300:
            target = ET.fromstring(resp['text'])
            if target.attrib['count'] == "0":
                await chan.send("No results found for that query.")
            else:
                target = random.choice(target).attrib
                source = target.get("source") or target.get("file_url")
                if not source.startswith("http"):
                    # milk junkies 02
                    source = target.get("file_url")
                timestring = datetime.datetime.strptime(target['created_at'], "%a %b %d %H:%M:%S %z %Y").strftime("%B %d, %Y")
                descrip = f"*posted {timestring}*\n\n**Score: {target['score']}**\n\n**Source:**\n{source}"
                image_url = target.get("sample_url")
                print(image_url)
                if image_url.endswith("webm"):
                    print("ok")
                    image_url = target.get("preview_url")
                    descrip += "***(animated)***"
                response_embed = Embed(url=source, type="rich",
                                       description=descrip, title="Rule34", color=0xa0e080)
                response_embed.set_image(url=image_url)
                response_embed.set_author(name="RULE34.XXX")
                await chan.send(embed=response_embed)
        else:
            await chan.send("Response failed. Remind me to provide more info here :)")
