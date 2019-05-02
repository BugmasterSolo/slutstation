import discord

from .base import Module, Command
import asyncio
import async_timeout
import time
import math
from youtube_dl import YoutubeDL
import os

opts = {
    "outtmpl": "~/Desktop/filecache/%(title)s.%(ext)s",  # temporary storage only. files are deleted after play; no limits yet :)
    "format": "bestaudio/best",
    "noplaylist": True,
    "default_search": "auto",
    "restrict_filenames": True
}  # add later

# add voting for skips and stops (admin trumps)
# polish out the code (bug test the stream_history deal)
# might be a good idea to rewrite this over the WKND (outside of grading :)
# with some better planning

ytdl = YoutubeDL(opts)

stream_history = {}


# purges unused streams once per hour. unused means it has not been played in 24 hours
# requeueing a stream within this period resets the counter.
async def check_stream_history():
    print("ok")
    while True:
        curtime = time.time()
        for key in stream_history:
            past = curtime - stream_history[key]
            if past > 86399:
                stream_history.pop(key)
                os.path.remove(key)
        await asyncio.sleep(3600)

loop = asyncio.get_event_loop()

loop.create_task(check_stream_history())  # task runs in bg, runtilcomplete is priority

# set up a once/hour loop that removes unused files from here


# hodged solution -- resolve quick + soon
class StreamContainer:
    def __init__(self, source, data, message, loc, embed):
        self.page_url = data['webpage_url']
        self.author = message.author
        self.title = data['title']
        self.thumb = data['thumbnail']
        self.description = data['description'][:200]
        self.channel = data['uploader']
        self.message_host = message.channel
        self.source = source
        self.dir = loc
        self.embed = embed
        if len(self.description) >= 200:
            self.description += "..."


# massive cred: https://gist.github.com/EvieePy/ab667b74e9758433b3eb806c53a19f34
# i don't think i would understand this shit otherwise
# btw: every impatient pencil pusher in the discordpy issue comments can eat shit
# non necessary, flush out (left over gunk and gook)
class YTPlayer:

    # If you want to find out whether a given URL is supported, simply call youtube-dl with it.
    # If you get no videos back, chances are the URL is either not referring to a video or unsupported.
    # You can find out which by examining the output (if you run youtube-dl on the console) or catching an
    # UnsupportedError exception if you run it from a Python program.
    @classmethod
    async def format_source_local(cls, host, state, url: str):  # partial bundles a function and args into a single callable
        try:
            data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url=url, download=False))  # asyncs synchronous function
        except PermissionError:
            await state.message.channel.send("Look, something went wrong. I'm sorry.")
            # ahaha
            # no joke: deal with this exception soon. something along the lines of:
            #   - fetch the false download case
            #   - prepare the file anyway
            #   - add a prng string based on some ambient system variables
            #   - cross fingers and hope
            pass

        if 'entries' in data:
            data = data['entries'][0]
            # tbd: get the whole playlist as YTPlayers
        # no way to get the path prior to search -- this works though
        source = ytdl.prepare_filename(data)
        if not os.path.exists(source):
            # synchronous blocking calls run in the executor
            data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url=url, download=True))
            if 'entries' in data:
                data = data['entries'][0]

        descrip = f"*{data['title']}\nby {data['uploader']}*"
        response_embed = discord.Embed(title="Added to queue!", color=0xff0000,
                                       description=descrip)
        response_embed.set_thumbnail(url=data['thumbnail'])
        return StreamContainer(source=discord.FFmpegPCMAudio(source), data=data, message=state.message, loc=source, embed=response_embed)  # gross

    async def tether_stream(self):
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url=self.page_url, download=False))
        return discord.FFmpegPCMAudio(data['url'])


# need some sort of key/val structure to remove files that haven't been called in 24 hours
class MusicPlayer:
    def __del__(self):
        print("im gone")

    def __init__(self, host, state, player):
        self.host = host                                            # Government
        self.source = state.message                                 # one player to a guild, you can't have the bot all to yourself
        self.queue = asyncio.Queue()                                # music queue for a given channel
        self.state = asyncio.Event()                                # used to ensure only one stream runs at a time
        self.active_vc = None                                       # the currently active voice client
        self.parent = player                                        # the "command_host", in this case our Player module
        self.voice_channel = state.message.author.voice.channel     # the currently active voice channel
        self.queue_event = asyncio.Event()
        self.skip_list = []

        self.queue_event.clear()
        loop.create_task(self.player())

    async def player(self):
        source = None

        channel = self.voice_channel
        if not self.active_vc:
            m = channel.guild.get_member(self.host.user.id)
            perm = channel.permissions_for(m)
            if not perm.connect:
                await self.source.channel.send("I can't join that voice channel!")  # only relevant on first play, we can use this channel
                self.queue_event.set()  # notify built ins that we're tossing the bunch
                await self.destroy()
                return
            self.active_vc = await channel.connect()
            self.queue_event.set()  # active_vc exists, so we're in the clear
        while True:
            self.state.clear()
            # runs per loop
            try:
                print("player initiated")
                async with async_timeout.timeout(60):
                    # if something goes wrong, wait for the queue to fill up.
                    source = await self.queue.get()
                    if not os.path.exists(source.dir):
                        await loop.run_in_executor(None, lambda: ytdl.extract_info(url=source.page_url, download=True))  # download is predictable
                    stream_history[source.dir] = time.time()
            except asyncio.TimeoutError:
                await self.source.channel.send("Disconnecting from current voice channel.")
                await self.destroy(self.directory)
                return
            channel = None
            channel = self.voice_channel  # guaranteed earlier
            stream = None
            # not necessary
            if isinstance(source, YTPlayer):
                try:
                    stream = await source.tether_stream()
                except Exception as e:
                    print(e)
                # check if already connected due to some bug.
            else:
                stream = source.source
            if not self.active_vc:
                m = channel.guild.get_member(self.host.user.id)
                perm = channel.permissions_for(m)
                if not perm.connect:
                    await source.message_host.send("I can't join that voice channel!")
                    break
                self.active_vc = await channel.connect()
            print("here")
            descrip = f"*{source.title}\nby {source.channel}*\n\n{source.description}"
            response_embed = discord.Embed(title="Now Playing!", color=0xff0000, description=descrip)
            response_embed.set_thumbnail(url=source.thumb)
            response_embed.set_footer(text=f"Added by {source.author.name}#{source.author.discriminator}",
                                      icon_url=source.author.avatar_url_as(static_format="png", size=128))
            self.active_vc.play(stream, after=lambda _: loop.call_soon_threadsafe(self.state.set))  # _ absorbs error handler
            await source.message_host.send(embed=response_embed)
            print("waiting...")
            await self.state.wait()
            print("song finished!")
            stream.cleanup()
            print("stream cleaned!")
            if self.queue.empty():
                break
                # destroy player here as well
        # loop over. destroy this instance.
        print("loop broken.")
        await self.destroy()

    # adds to queue. ignores if process fails.
    async def add_to_queue(self, stream):
        await self.queue_event.wait()
        if self.active_vc:
            await self.queue.put(stream)
            await self.source.channel.send(embed=stream.embed)

    # integrate permissions into here (and all over frankly)
    async def process_skip(self, member):
        # member count is important here, so let's get the channel again
        self.voice_channel = self.host.get_guild(self.source.guild.id).voice_client.channel  # i mean this should exist i think
        listener_threshold = math.ceil(len(self.voice_channel.members)) - 1  # bot doesn't count
        if member in self.voice_channel.members:
            if member not in self.skip_list:
                self.skip_list.append(member)
                skip_count = len(self.skip_list)
                if skip_count >= listener_threshold:
                    self.active_vc.stop()
                    await self.source.channel.send("Song skipped!")
                else:
                    await self.source.channel.send(f"User {member.name}#{member.discriminator} voted to skip.\n{skip_count}/{listener_threshold} votes.")
            else:
                self.skip_list.remove(member)
                await self.source.channel.send("User {member.name}#{member.discriminator} unskipped.\n{skip_count}/{listener_threshold} votes.")
        else:
            await self.source.channel.send("nice try bucko")


    async def destroy(self):
        if self.active_vc:
            self.active_vc.stop()
            await self.active_vc.disconnect()
        self.parent.pop_player(self.source.guild.id)
        del self


# todo: add proper exception for invalid URL
# run through some edge case tests over the next few days
class Player(Module):
    def __init__(self, host, *args, **kwargs):
        super().__init__(host, *args, **kwargs)
        self.active_players = {}

    def get_player(self, host, state):
        player = self.active_players.get(state.message.guild.id)
        if not player:
            player = MusicPlayer(host, state, self)
            self.active_players[state.message.guild.id] = player
        print(player)
        return player

    def pop_player(self, id):
        self.active_players.pop(id)

    @Command.register(name="play")
    async def play(host, state):
        # call the proper instance of ytdl
        if not state.message.author.voice:
            await state.message.channel.send("Please join a voice channel first!")
            return
        # no idea why this does not work
        player = state.command_host.active_players.get(state.message.guild.id)
        if player is not None and player.active_vc.is_paused():
            player.active_vc.resume()
        url = Command.split(state.content)
        print(url)
        url = url[0]
        if not url.startswith("http"):
            await state.message.channel.send("Please pass a valid URL.")
            return
        player = state.command_host.get_player(host, state)
        source = await YTPlayer.format_source_local(host, state, url=url)
        stream_history[source.dir] = time.time()  # queue once when downloaded.
        print("source formatted")
        print(player)
        await player.add_to_queue(source)

    @Command.register(name="pause")
    async def pause(host, state):
        player = state.command_host.active_players.get(state.message.guild.id)
        if player:
            player.active_vc.pause()
        else:
            await state.message.channel.send("*i didn't even play anything...")

    # throws an error, check it out later.
    @Command.register(name="stop")
    async def stop(host, state):
        player = state.command_host.active_players.get(state.message.guild.id)
        if player:
            del player.queue
            player.queue = asyncio.Queue()  # sub the queue for an empty one (probably better way to accomp)
            player.active_vc.stop()

    @Command.register(name="skip")
    async def skip(host, state):
        player = state.command_host.active_players.get(state.message.guild.id)
        if player:
            await player.process_skip(state.message.author)
