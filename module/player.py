import discord

from .base import Module, Command
from functools import partial
import asyncio
import async_timeout
from youtube_dl import YoutubeDL

# pwd: government
opts = {
    "output": "temp/%(title)s.%(ext)s",  # enables download
    "format": "bestaudio/best",
    "default_search": "auto",
    "restrict_filenames": True
}  # add later

#  the player is a persistent object that hosts a queue
#  the queue can be added to as necessary and we can read from it!

#  thus the only difficult thing is getting the information into the audio class

#  it works, now rebuild it

ytdl = YoutubeDL(opts)


# source defines the stream for the actual player
# inheirits from ffmpegp
# some way of getting guild index
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
    async def format_source(cls, host, state, url: str):
        loop = host.loop
        infop = partial(ytdl.extract_info, url=url, download=False)  # partial bundles a function and args into a single callable
        data = await loop.run_in_executor(None, infop)  # asyncs synchronous function

        if 'entries' in data:
            data = data['entries'][0]
            # tbd: get the whole playlist as YTPlayers
        descrip = f"*{data['title']}\nby {data['uploader']}*"
        response_embed = discord.Embed(title="Added to queue!", color=0xff0000,
                                       description=descrip)
        response_embed.set_thumbnail(url=data['thumbnail'])
        await state.message.channel.send(embed=response_embed)
        return cls(data=data, message=state.message, loop=loop)

    async def tether_stream(self):
        infop = partial(ytdl.extract_info, url=self.page_url, download=False)
        data = await self.loop.run_in_executor(None, infop)
        return discord.FFmpegPCMAudio(data['url'])


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

        # kicks off the play loop
#        host.loop.create_task(self.queue.put({
#            #  my guess: url returns a temporary stream
#            'webpage_url': "https://www.youtube.com/watch?v=V5v6WijK1xg",
#            'user': state.message.author,
#            'title': "monkey"
#        }))

        # kicks off the loop
        # create_task is our sync/async tether, allowing us to schedule this task.

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
            except asyncio.TimeoutError:
                await self.source.channel.send("Disconnecting from current voice channel.")
                await self.destroy()
                return
            channel = None
            try:
                print(source.author)
                print(source.author.voice)
                channel = source.author.voice.channel

            except Exception as e:
                print("hehemoment")
                print(e)
                await self.destroy()
            stream = None
            try:
                stream = await source.tether_stream()
            except Exception as e:
                print("Something went wrong while getting the stream!")
                print(e)
            # check if already connected due to some bug.
            if not self.active_vc:
                self.active_vc = await channel.connect()

            descrip = f"*{source.title}\nby {source.channel}*\n\n{source.description}"
            response_embed = discord.Embed(title="Now Playing!", color=0xff0000, description=descrip, thumbnail=source.thumb)
            response_embed.set_footer(text=f"Added by {source.author.name}#{source.author.discriminator}",
                                      icon_url=source.author.avatar_url_as(static_format="png", size=128))
            self.active_vc.play(stream, after=lambda _: self.host.loop.call_soon_threadsafe(self.state.set))
            await source.message_host.send(embed=response_embed)

            await self.state.wait()
            print("song finished!")
            stream.cleanup()
            if self.queue.empty():
                break
                # destroy player here as well
        # loop over. destroy this instance.
        await self.destroy()

    async def destroy(self):
        await self.active_vc.disconnect()
        self.parent.pop_player(self.source.guild.id)
        print(self.parent.active_players)
        del self


# todo: add proper exception for invalid URL
class Player(Module):
    def __init__(self, host, *args, **kwargs):
        super().__init__(host, *args, **kwargs)
        self.active_players = {}
        self.isPaused = False

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
        source = await YTPlayer.format_source(host, state, url=url)
        print("source formatted")
        await player.queue.put(source)

    @Command.register(name="pause")
    async def pause(host, state):
        player = state.command_host.active_players.get(state.message.guild.id)
        if player:
            player.active_vc.pause()
        else:
            await state.message.channel.send("*i didn't even play anything...")