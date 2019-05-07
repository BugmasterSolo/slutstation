import discord

from .base import Module, Command
import asyncio
import async_timeout
import time
import math
import json
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
# might want to move this into player module
async def check_stream_history():
    while True:
        print("Purging stream cache...")
        curtime = time.time()
        for key in stream_history:
            past = curtime - stream_history[key]
            if past > 10799:
                loop.run_in_executor(None, lambda: os.remove(key))
                print(f"Deleted item in directory {key} .")
                stream_history.pop(key)
        await asyncio.sleep(3600)

loop = asyncio.get_event_loop()

loop.create_task(check_stream_history())  # task runs in bg, runtilcomplete is priority


def format_time(time):
    min = math.floor(time / 60)
    sec = math.floor(time % 60)
    if sec < 10:
        sec = f"0{sec}"
    return f"{min}:{sec}"

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
        self.duration = data['duration']
        self.message_host = message.channel
        self.source = source
        self.dir = loc
        self.embed = embed
        if len(self.description) >= 200:
            self.description += "..."
        print(self.duration)


# massive cred: https://gist.github.com/EvieePy/ab667b74e9758433b3eb806c53a19f34
# i don't think i would understand this shit otherwise
# btw: every impatient pencil pusher in the discordpy issue comments can eat shit
# non necessary, flush out (left over gunk and gook)
# param types: https://stackoverflow.com/questions/2489669/function-parameter-types-in-python
class YTPlayer:

    # from the docs:
    #   If you want to find out whether a given URL is supported, simply call youtube-dl with it.
    #   If you get no videos back, chances are the URL is either not referring to a video or unsupported.
    #   You can find out which by examining the output (if you run youtube-dl on the console) or catching an
    #   UnsupportedError exception if you run it from a Python program.
    async def format_source_local(host, state, url: str):  # partial bundles a function and args into a single callable (url of type str)
        try:
            data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url=url, download=False))  # asyncs synchronous function
        except PermissionError:
            print("exc")
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
        source = ytdl.prepare_filename(data)
        if not os.path.exists(source):
            # synchronous blocking calls run in the executor
            data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url=url, download=True))
            if 'entries' in data:  # duped
                data = data['entries'][0]
        descrip = f"*{data['title']}\nby {data['uploader']}*\n\n**Duration: {format_time(data['duration'])}**"
        response_embed = discord.Embed(title="Added to queue!", color=0xff0000,
                                       description=descrip, url=data['webpage_url'])
        response_embed.set_thumbnail(url=data['thumbnail'])
        return StreamContainer(source=discord.FFmpegPCMAudio(source), data=data, message=state.message, loc=source, embed=response_embed)  # gross


# need some sort of key/val structure to remove files that haven't been called in 24 hours
class MusicPlayer:
    def __init__(self, host, state, player):
        self.host = host                                            # Government
        self.source = state.message                                 # one player to a guild, you can't have the bot all to yourself
        self.queue = asyncio.Queue()                                # music queue for a given channel
        self.state = asyncio.Event()                                # used to ensure only one stream runs at a time
        self.active_vc = None                                       # the currently active voice client
        self.parent = player                                        # the "command_host", in this case our Player module
        self.voice_channel = state.message.author.voice.channel     # the currently active voice channel
        self.queue_event = asyncio.Event()                          # tbh im pretty sure i can get rid of this
        self.skip_list = []                                         # tracks the number of users willing to skip
        self.now_playing = None                                     # embed representing currently playing song
        self.queue_duration = 0                                     # current queue duration (s)
        self.start_time = time.time()                               # start time of player (unix epoch)
        self.last_start_time = None                                 # start time of last track
        self.now_playing_duration = None                            # duration of current track
        self.queue_event.clear()
        loop.create_task(self.player())

    async def player(self):
        source = None

        channel = self.voice_channel
        if not self.active_vc:
            m = await loop.run_in_executor(None, lambda: channel.guild.get_member(self.host.user.id))
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
                    async with async_timeout.timeout(120):
                        # if something goes wrong, wait for the queue to fill up. this works when delays appear in the DL process.
                        source = await self.queue.get()
                        if not os.path.exists(source.dir):
                            await loop.run_in_executor(None, lambda: ytdl.extract_info(url=source.page_url, download=True))  # download is predictable
                        stream_history[source.dir] = time.time()
                except asyncio.TimeoutError:
                    await self.source.channel.send("Failed to fetch source. Disconnecting from current voice channel.")
                    await self.destroy()
                    return
                channel = self.voice_channel  # guaranteed earlier
                stream = source.source  # we're always downloadin ...
                if not self.active_vc:
                    m = channel.guild.get_member(self.host.user.id)  # frustrating
                    perm = channel.permissions_for(m)
                    if not perm.connect:
                        await source.message_host.send("I can't join that voice channel!")
                        break
                    self.active_vc = await channel.connect()
                duration_string = format_time(source.duration)
                descrip = f"*{source.title}\nby {source.channel}*\n\n**Duration:** {duration_string}\n\n{source.description}"
                response_embed = discord.Embed(title="Now Playing!", color=0xff0000, description=descrip, url=source.page_url)
                response_embed.set_thumbnail(url=source.thumb)
                response_embed.set_footer(text=f"Added by {source.author.name}#{source.author.discriminator}",
                                          icon_url=source.author.avatar_url_as(static_format="png", size=128))
                self.now_playing_duration = source.duration  # optimize
                self.active_vc.play(stream, after=lambda _: loop.call_soon_threadsafe(self.state.set))  # _ absorbs error handler
                self.last_start_time = time.time()
                await self.source.channel.send(embed=response_embed)  # this zone is definitely safe
                self.now_playing = response_embed
                await self.state.wait()
                stream.cleanup()
                if self.queue.empty():
                    break
                    # destroy player here as well
            # loop over. destroy this instance.
            await self.destroy()

    # adds to queue. ignores if process fails.
    async def add_to_queue(self, stream):
        await self.queue_event.wait()
        if self.active_vc:
            await self.queue.put(stream)
            time_until_playing = max((self.queue_duration + self.start_time) - time.time(), 0)
            duration_string = format_time(time_until_playing)
            self.queue_duration += stream.duration
            stream.embed.set_footer(text=("\n\nTime until playing: " + duration_string))
            await self.source.channel.send(embed=stream.embed)

    # integrate permissions into here (and all over frankly)
    async def process_skip(self, member):
        # member count is important here, so let's get the channel again
        self.voice_channel = self.host.get_guild(self.source.guild.id).voice_client  # i mean this should exist i think
        if self.voice_channel is None:
            print("Error in voice. Disconnecting completely.")
            pass
        self.voice_channel = self.voice_channel.channel
        listener_threshold = math.ceil((len(self.voice_channel.members) - 1) / 2)  # bot doesn't count
        if member in self.voice_channel.members:
            if member not in self.skip_list:
                self.skip_list.append(member)
                skip_count = len(self.skip_list)
                if skip_count >= listener_threshold:
                    # on skip: add skipped time to start time
                    self.active_vc.stop()
                    time_skip = self.now_playing_duration - (time.time() - self.last_start_time)
                    self.queue_duration -= time_skip  # retain context of start time in case it matters
                    await self.source.channel.send("Song skipped!")
                    self.skip_list.clear()
                else:
                    await self.source.channel.send(f"User {member.name}#{member.discriminator} voted to skip.\n{skip_count}/{listener_threshold} votes.")
            else:
                self.skip_list.remove(member)
                await self.source.channel.send(f"User {member.name}#{member.discriminator} unskipped.\n{skip_count}/{listener_threshold} votes.")
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
        with open("youtube_api.txt", "r") as ytapi:
            self.api_key = ytapi.read().strip()

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
        chan = state.message.channel
        if not state.message.author.voice:
            await state.message.channel.send("Please join a voice channel first!")
            return
        # no idea why this does not work
        player = state.command_host.active_players.get(state.message.guild.id)
        url = state.content  # todo: deal with additional arguments
        if len(url) == 0:
            if not player:  # inactive -- url required
                await chan.send("Please provide a valid URL!")
                return  # if paused: skips if cases
            else:  # something playing
                if player.is_playing():  # no url, playing already
                    await chan.send("I'm already playing something!")
                    return
                elif player.active_vc.is_paused():  # no url, paused (active)
                    player.active_vc.resume()
        if not url.startswith("http"):
            # engage search api
            # if search then include all queries
            return_query = await Module._http_get_request(f"https://www.googleapis.com/youtube/v3/search?part=snippet&maxResults=25&q={state.content}&type=video&key={state.command_host.api_key}")
            return_query = json.loads(return_query['text'])
            if len(return_query['items']) == 0:
                await chan.send("No results found for that query.")
                return
            return_query = return_query['items'][0]
            url = "https://www.youtube.com/watch?v=" + return_query['id']['videoId']
        msg = await chan.send("```Searching...```")
        await chan.trigger_typing()
        try:
            source = await YTPlayer.format_source_local(host, state, url=url)
        except Exception as e:  # dont know the error type
            await chan.send("Something went wrong while processing that link. Feel free to try it again though.")
            print(e)
            await msg.delete()
            return

        player = state.command_host.get_player(host, state)
        stream_history[source.dir] = time.time()  # queue once when downloaded.
        await msg.delete()
        print("added")
        await player.add_to_queue(source)

    @Command.register(name="pause")
    async def pause(host, state):
        player = state.command_host.active_players.get(state.message.guild.id)
        if player:
            player.active_vc.pause()
        else:
            await state.message.channel.send("*i didn't even play anything...*")

    # throws an error, check it out later.
    @Command.register(name="stop")
    async def stop(host, state):
        # check if admin
        perms = state.message.author.permissions_in(state.message.channel)
        player = state.command_host.active_players.get(state.message.guild.id)
        if perms.administrator:
            if player:
                del player.queue
                player.queue = asyncio.Queue()  # sub the queue for an empty one (probably better way to accomp)
                player.active_vc.stop()  # stop the current stream, calling on the empty queue
        else:
            await state.message.channel.send("\U0001f6d1 | **You do not have permission to stop the stream. Use 'g skip' instead!** | \U0001f6d1")

    @Command.register(name="skip")
    async def skip(host, state):
        player = state.command_host.active_players.get(state.message.guild.id)
        if player:
            await player.process_skip(state.message.author)

    @Command.register(name="playing")
    async def now_playing(host, state):
        player = state.command_host.active_players.get(state.message.guild.id)
        embed = None
        if player:
            embed = player.now_playing
        if not player or not embed:
            await state.message.channel.send("*Nothing is currently playing!*")
        else:
            await state.message.channel.send(embed=embed)
