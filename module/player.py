import discord

from .base import Module, Command
from functools import partial
import asyncio
import async_timeout
import time
from youtube_dl import YoutubeDL
import os

opts = {
    "outtmpl": "~/Desktop/filecache/%(title)s.%(ext)s",  # temporary storage only. files are deleted after play; no limits yet :)
    "format": "bestaudio/best",
    "default_search": "auto",
    "restrict_filenames": True
}  # add later

ytdl = YoutubeDL(opts)

stream_history = {}

# set up a once/hour loop that removes unused files from here


# hodged solution -- resolve quick + soon
class StreamContainer:
    def __init__(self, source, data, message, loop, loc):
        self.page_url = data['webpage_url']
        self.author = message.author
        self.title = data['title']
        self.thumb = data['thumbnail']
        self.description = data['description'][:200]
        self.channel = data['uploader']
        self.message_host = message.channel
        self.loop = loop
        self.source = source
        self.dir = loc
        if len(self.description) >= 200:
            self.description += "..."


# massive cred: https://gist.github.com/EvieePy/ab667b74e9758433b3eb806c53a19f34
class YTPlayer:
    def __init__(self, *, data, message, loop):
        self.page_url = data['webpage_url']
        self.author = message.author
        self.title = data['title']
        self.thumb = data['thumbnail']
        self.description = data['description'][:200]
        self.channel = data['uploader']
        self.message_host = message.channel
        self.loop = loop
        if len(self.description) >= 200:
            self.description += "..."
        # init'd on add, this is ok.
        # apparently we can't save the stream but might be worth? nah probably not

    @classmethod
    async def format_source_local(cls, host, state, url: str):
        loop = host.loop
        infop = partial(ytdl.extract_info, url=url, download=False)  # partial bundles a function and args into a single callable
        try:
            data = await loop.run_in_executor(None, infop)  # asyncs synchronous function
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
            infop = partial(ytdl.extract_info, url=url, download=True)
            data = await loop.run_in_executor(None, infop)
            if 'entries' in data:
                data = data['entries'][0]
        descrip = f"*{data['title']}\nby {data['uploader']}*"
        response_embed = discord.Embed(title="Added to queue!", color=0xff0000,
                                       description=descrip)
        response_embed.set_thumbnail(url=data['thumbnail'])
        await state.message.channel.send(embed=response_embed)

        return StreamContainer(source=discord.FFmpegPCMAudio(source), data=data, message=state.message, loop=loop, loc=source)

    async def tether_stream(self):
        infop = partial(ytdl.extract_info, url=self.page_url, download=False)
        data = await self.loop.run_in_executor(None, infop)
        return discord.FFmpegPCMAudio(data['url'])


# need some sort of key/val structure to remove files that haven't been called in 24 hours
class MusicPlayer:
    def __del__(self):
        print("im gone")

    def __init__(self, host, state, player):
        self.host = host
        self.source = state.message  # one player to a guild, you can't have the bot all to yourself
        self.queue = asyncio.Queue()
        self.state = asyncio.Event()
        host.loop.create_task(self.player())
        self.active_vc = None
        self.parent = player

    async def player(self):
        source = None
        print("test")
        while True:
            self.state.clear()
            # runs per loop
            try:
                print("player initiated")
                # waits 60 seconds until the item is available
                async with async_timeout.timeout(60):
                    source = await self.queue.get()
                    stream_history[source.dir] = time.time()
            except asyncio.TimeoutError:
                await self.source.channel.send("Disconnecting from current voice channel.")
                await self.destroy(self.directory)
                return
            channel = None
            try:
                channel = source.author.voice.channel

            except Exception as e:
                print("hehemoment")
                print(e)
                await self.destroy(self.directory)
            stream = None
            if isinstance(source, YTPlayer):
                try:
                    stream = await source.tether_stream()
                except Exception as e:
                    print("Something went wrong while getting the stream!")
                    print(e)
                # check if already connected due to some bug.
            else:
                stream = source.source
            if not self.active_vc:
                self.active_vc = await channel.connect()

            descrip = f"*{source.title}\nby {source.channel}*\n\n{source.description}"
            response_embed = discord.Embed(title="Now Playing!", color=0xff0000, description=descrip, thumbnail=source.thumb)
            response_embed.set_footer(text=f"Added by {source.author.name}#{source.author.discriminator}",
                                      icon_url=source.author.avatar_url_as(static_format="png", size=128))
            self.active_vc.play(stream, after=lambda _: self.host.loop.call_soon_threadsafe(self.state.set))  # ok this lambda carried over
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

    # evidently disconnecting the vc calls destroy
    # incorporating this into the del statement may be more reliable
    async def destroy(self, isStopped=False):
        await self.active_vc.disconnect()
        if not isStopped:
            self.parent.pop_player(self.source.guild.id)
        del self


# todo: add proper exception for invalid URL
class Player(Module):
    def __init__(self, host, *args, **kwargs):
        super().__init__(host, *args, **kwargs)
        self.active_players = {}

    def get_player(self, host, state):
        player = self.active_players.get(state.message.guild.id)
        if not player:
            player = MusicPlayer(host, state, self)
            self.active_players[state.message.guild.id] = player
        return player

    def pop_player(self, id):
        self.active_players.pop(id)

    @Command.register(name="play")
    async def play(host, state):
        # call the proper instance of ytdl
        if not state.message.author.voice:
            await state.message.channel.send("Please join a voice channel first!")
            return
        player = state.command_host.active_players.get(state.message.guild.id)
        if player and player.active_vc.is_paused():
            player.active_vc.resume()
        url = Command.split(state.content)
        print(url)
        url = url[0]
        if not url.startswith("http"):
            if not player:
                await state.message.channel.send("Please pass a valid URL.")
            return
        player = state.command_host.get_player(host, state)
        source = await YTPlayer.format_source_local(host, state, url=url)
        print("source formatted")
        await player.queue.put(source)

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
            await player.destroy(True)
