import discord

from .base import Module, Command, GuildUpdateListener, HTTPNotFoundException
import asyncio
import async_timeout
import time
import math
import json
import re
from youtube_dl import YoutubeDL

opts = {
    "outtmpl": "~/Desktop/filecache/%(title)s.%(ext)s",
    "format": "bestaudio/best",
    "noplaylist": True,
    "default_search": "auto",
    "restrict_filenames": True
}


class DurationError(Exception):
    pass


ytdl = YoutubeDL(opts)

loop = asyncio.get_event_loop()


def format_time(time):
    min = math.floor(time / 60)
    sec = math.floor(time % 60)
    if sec < 10:
        sec = f"0{sec}"
    return f"{min}:{sec}"


class StreamContainer:
    __slots__ = ['page_url', 'author', 'title', 'thumb', 'description', 'channel', 'duration', 'message_host', 'source', 'dir', 'embed']

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


class StreamGenerator:
    def __init__(self, gen, embed):
        self.gen = gen
        self.embed = embed


# massive cred: https://gist.github.com/EvieePy/ab667b74e9758433b3eb806c53a19f34
# i don't think i would understand this shit otherwise
# btw: every impatient pencil pusher in the discordpy issue comments can eat shit
# param types: https://stackoverflow.com/questions/2489669/function-parameter-types-in-python
class YTPlayer:

    @staticmethod
    async def format_source_local(host, state, url):
        if not isinstance(url, str):
            return YTPlayer.format_source_tuple(host, state, url)
        else:
            return await YTPlayer.format_source_single(host, state, url)

    # from the docs:
    #   If you want to find out whether a given URL is supported, simply call youtube-dl with it.
    #   If you get no videos back, chances are the URL is either not referring to a video or unsupported.
    #   You can find out which by examining the output (if you run youtube-dl on the console) or catching an
    #   UnsupportedError exception if you run it from a Python program.
    @staticmethod
    async def format_source_single(host, state, url):
        try:
            data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url=url, download=False))
        except PermissionError:
            await state.message.channel.send("Look, something went wrong. I'm sorry.")

        if 'entries' in data:
            data = data['entries'][0]
        descrip = f"*{data['title']}\nby {data['uploader']}*\n\n**Duration: {format_time(data['duration'])}**"
        response_embed = discord.Embed(title="Added to queue!", color=0xff0000,
                                       description=descrip, url=data['webpage_url'])
        response_embed.set_thumbnail(url=data['thumbnail'])
        return StreamContainer(source=discord.FFmpegPCMAudio(data['url'], before_options="-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"), data=data, message=state.message, loc=None, embed=response_embed)
        # this makes the streaming work by reconnecting to the stream

    @staticmethod
    def format_source_tuple(host, state, url):
        async def generator():
            for link in url:
                player = await YTPlayer.format_source_single(host, state, link)  # eek
                yield player
        author = state.message.author
        response_embed = discord.Embed(title=f"Added {len(url)} videos to queue!", color=0xff0000)
        response_embed.set_footer(text=f"Added by {author.name}#{author.discriminator}",
                                  icon_url=author.avatar_url_as(static_format="png", size=128))
        return StreamGenerator(generator, response_embed)


def check(guild_old, guild_new):
    return guild_old.region != guild_new.region


class MusicPlayer:
    __slots__ = ['host', 'source', 'queue', 'state', 'active_vc', 'parent', 'voice_channel', 'queue_event', 'skip_list', 'now_playing', 'queue_duration', 'start_time', 'last_start_time', 'now_playing_duration', 'destroyed', 'listener']

    def __init__(self, host, state, player, channel):
        self.host = host                                            # Government
        self.source = state.message                                 # one player to a guild, you can't have the bot all to yourself
        self.queue = asyncio.Queue()                                # music queue for a given channel
        # queue is necessary for async.
        self.state = asyncio.Event()                                # used to ensure only one stream runs at a time
        self.active_vc = None                                       # the currently active voice client
        self.parent = player                                        # the "command_host", in this case our Player module
        self.voice_channel = channel                                # the currently active voice channel
        self.queue_event = asyncio.Event()                          # tbh im pretty sure i can get rid of this
        self.skip_list = []                                         # tracks the number of users willing to skip
        self.now_playing = None                                     # embed representing currently playing song
        self.queue_duration = 0                                     # current queue duration (s)
        self.start_time = time.time()                               # start time of player (unix epoch)
        self.last_start_time = None                                 # start time of last track
        self.now_playing_duration = None                            # duration of current track
        self.queue_event.clear()
        self.destroyed = False                                      # backup destroy flag (lazy)
        loop.create_task(self.player())

        # come up with a shit fix for this
        async def update_vc(guild_new):
            self.queue = asyncio.Queue()
            self.active_vc.stop()
            await self.source.channel.send("Disconnecting due to region switch. It conks out otherwise, let me know if you can fix it :)")

        self.listener = GuildUpdateListener(state.message.guild, check, update_vc)

        self.host.loop.create_task(self.host.add_guild_update_listener(self.listener))

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
                    async with async_timeout.timeout(180):
                        # if something goes wrong, wait for the queue to fill up. this works when delays appear in the DL process.
                        source = await self.queue.get()
                except asyncio.TimeoutError:
                    await self.source.channel.send("Failed to fetch source. Disconnecting from current voice channel.")
                    await self.destroy()
                    return
                if isinstance(source, StreamGenerator):
                    async for stream in source.gen():
                        await self.play_stream(stream.source, stream)
                else:
                    await self.play_stream(source.source, source)
                if self.queue.empty() or self.destroyed:
                    break
            await self.destroy()

    async def play_stream(self, stream, source):
        self.state.clear()
        channel = self.voice_channel
        if not self.active_vc:
            m = channel.guild.get_member(self.host.user.id)
            perm = channel.permissions_for(m)
            if not perm.connect:
                await source.message_host.send("I can't join that voice channel!")
                return
            self.active_vc = await channel.connect()
        self.active_vc = channel.guild.voice_client

        duration_string = format_time(source.duration)
        descrip = f"*{source.title}\nby {source.channel}*\n\n**Duration:** {duration_string}\n\n{source.description}"
        response_embed = discord.Embed(title="Now Playing!", color=0xff0000, description=descrip, url=source.page_url)
        response_embed.set_thumbnail(url=source.thumb)
        response_embed.set_footer(text=f"Added by {source.author.name}#{source.author.discriminator}",
                                  icon_url=source.author.avatar_url_as(static_format="png", size=128))
        self.now_playing_duration = source.duration  # optimize
        self.active_vc.play(stream, after=lambda _: loop.call_soon_threadsafe(self.state.set))
        self.last_start_time = time.time()
        await self.source.channel.send(embed=response_embed)
        self.now_playing = response_embed
        await self.state.wait()
        stream.cleanup()

    # adds to queue. ignores if process fails.
    async def add_to_queue(self, stream, chan):
        await self.queue_event.wait()
        if self.active_vc:
            await self.queue.put(stream)
            if isinstance(stream, StreamGenerator):
                self.queue_duration = None  # stream generator voids duration
                await chan.send(embed=stream.embed)
                return
            if self.queue_duration is not None:
                time_until_playing = max((self.queue_duration + self.start_time) - time.time(), 0)
                duration_string = format_time(time_until_playing)
                self.queue_duration += stream.duration
                stream.embed.set_footer(text=("\n\nTime until playing: " + duration_string))
            await chan.send(embed=stream.embed)

    # integrate permissions into here (and all over frankly)
    async def process_skip(self, member, chan):
        self.voice_channel = self.host.get_guild(self.source.guild.id).voice_client
        if self.voice_channel is None:
            print("Error in voice. Disconnecting completely.")
            self.destroy()
        self.voice_channel = self.voice_channel.channel
        listener_threshold = math.ceil((len(self.voice_channel.members) - 1) / 2)  # bot doesn't count
        perms = chan.permissions_for(member)
        if member in self.voice_channel.members:
            if perms.administrator:
                await self.operate_skip(chan)
            elif member not in self.skip_list:
                self.skip_list.append(member)
                skip_count = len(self.skip_list)
                if skip_count >= listener_threshold:
                    # on skip: add skipped time to start time
                    await self.operate_skip(chan)
                else:
                    await chan.send(f"User {member.name}#{member.discriminator} voted to skip.\n{skip_count}/{listener_threshold} votes.")
            else:
                self.skip_list.remove(member)
                await chan.send(f"User {member.name}#{member.discriminator} unskipped.\n{skip_count}/{listener_threshold} votes.")
        else:
            await chan.send("nice try bucko")

    async def operate_skip(self, chan):
        self.active_vc.stop()
        if self.queue_duration is not None:
            time_skip = self.now_playing_duration - (time.time() - self.last_start_time)
            self.queue_duration -= time_skip
        await chan.send("Song skipped!")
        self.skip_list.clear()

    async def destroy(self):
        self.destroyed = True
        if self.active_vc:
            self.active_vc.stop()
            await self.active_vc.disconnect()
        self.parent.pop_player(self.source.guild.id)
        await self.host.remove_guild_update_listener(self.listener)
        del self


# todo: add proper exception for invalid URL
# run through some edge case tests over the next few days
class Player(Module):
    def __init__(self, host, *args, **kwargs):
        super().__init__(host, *args, **kwargs)
        self.active_players = {}
        with open("youtube_api.txt", "r") as ytapi:
            self.api_key = ytapi.read().strip()

    def get_player(self, host, state, vchan):
        player = self.active_players.get(state.message.guild.id)
        if not player:
            player = MusicPlayer(host, state, self, vchan)
            self.active_players[state.message.guild.id] = player
        return player

    def pop_player(self, id):
        self.active_players.pop(id)

    @Command.register(name="play")
    async def play(self, host, state):
        '''
Bot will sing a song for you.

Sometimes fails to fetch music, since Youtube blocks content ID'd videos on the bot. We're working on it.

Fetches a link if provided, otherwise searches the query on Youtube.

If paused, resumes playback.

Usage:
g play (<valid URL> or <search query>)
        '''
        # TODO: double prints at times -- check out syntax for invalid urls.
        # PLUS: look into better arrow handling
        # call the proper instance of ytdl
        chan = state.message.channel
        msg = await chan.send("`Searching...`")
        if not state.message.author.voice:
            await state.message.channel.send("Please join a voice channel first!")
            return
        vchan = state.message.author.voice.channel
        # no idea why this does not work
        player = self.active_players.get(state.message.guild.id)
        url = state.content.strip()  # todo: deal with additional arguments
        print(url)
        is_playlist = re.search(r"playlist\?list=(?P<playlist_id>\w+)", url)
        if len(url) == 0:
            if not player:  # inactive -- url required
                await chan.send("Please provide a valid URL!")
                return  # if paused: skips if cases
            else:  # something playing
                if player.active_vc.is_playing():  # no url, playing already
                    await chan.send("I'm already playing something!")
                    return
                elif player.active_vc.is_paused():  # no url, paused (active)
                    player.active_vc.resume()
                    return
        if not url.startswith("http"):
            # engage search api
            # if search then include all queries
            try:
                return_query = await host.http_get_request(f"https://www.googleapis.com/youtube/v3/search?part=snippet&maxResults=25&q={state.content}&type=video&key={self.api_key}")
            except HTTPNotFoundException:
                await chan.send("Video search failed.")
                return
            return_query = json.loads(return_query['text'])
            if len(return_query['items']) == 0:
                await chan.send("No results found for that query.")
                return
            return_query = return_query['items'][0]
            url = "https://www.youtube.com/watch?v=" + return_query['id']['videoId']
        elif is_playlist:
            playlist_id = is_playlist.group("playlist_id")
            try:
                return_query = await host.http_get_request(f"https://www.googleapis.com/youtube/v3/playlistItems?part=id%2CcontentDetails&maxResults=50&playlistId={playlist_id}&key={self.api_key}")
            except HTTPNotFoundException:
                await chan.send("Playlist lookup failed.")
                return
            return_query = json.loads(return_query['text'])
            if len(return_query['items']) == 0:
                await chan.send("Invalid playlist ID.")
                return
            result_remain = return_query['pageInfo']['totalResults'] - 50
            url_list = [item['contentDetails']['videoId'] for item in return_query['items']]
            while result_remain > 0:
                page_token = return_query['nextPageToken']
                try:
                    return_query = await host.http_get_request(f"https://www.googleapis.com/youtube/v3/playlistItems?part=id%2CcontentDetails&maxResults=50&playlistId={playlist_id}&pageToken={page_token}&key={self.api_key}")
                except HTTPNotFoundException:
                    await chan.send("Playlist lookup failed.")
                    return
                return_query = json.loads(return_query['text'])
                returnlen = len(return_query['items'])
                if returnlen > 0:
                    url_list += [item['contentDetails']['videoId'] for item in return_query['items']]
                    result_remain = result_remain - returnlen
                else:
                    result_remain = 0  # something went wrong and we are done now
            url = url_list
        await chan.trigger_typing()
        try:
            source = await YTPlayer.format_source_local(host, state, url=url)
        except Exception as e:  # dont know the error type
            if isinstance(e, DurationError):
                await chan.send("Keep your songs below 2 hours, please :)")
            else:
                await chan.send("Something went wrong while processing that link. Feel free to try it again though.")
                print(e)
            await msg.delete()
            return
        player = self.get_player(host, state, vchan)
        await msg.delete()
        await player.add_to_queue(source, state.message.channel)

    # deal with case where user keeps the bot paused.
    @Command.register(name="pause")
    async def pause(self, host, state):
        '''
Pauses currently playing video. Only works if the bot is already in a call.

Usage:
g pause
        '''
        player = self.active_players.get(state.message.guild.id)
        if player:
            player.active_vc.pause()
        else:
            await state.message.channel.send("*i didn't even play anything...*")

    @Command.register(name="stop")
    async def stop(self, host, state):
        '''
Administrator only. Stops current playback, if playing.

Usage:
g stop
        '''
        # check if admin
        perms = state.message.author.permissions_in(state.message.channel)
        player = self.active_players.get(state.message.guild.id)
        if perms.administrator:
            if player:
                player.destroyed = True
                player.active_vc.stop()  # stop the current stream, calling on the empty queue
        else:
            await state.message.channel.send("\U0001f6d1 | **You do not have permission to stop the stream. Use 'g skip' instead!** | \U0001f6d1")

    @Command.register(name="skip")
    async def skip(self, host, state):
        '''
Submits a skip request to the bot.

If user is an administrator, the skip is processed immediately.
Otherwise it's added to a vote tally of users. Once the majority of users in the call votes to skip, the video is skipped.

Usage:
g skip
        '''
        player = self.active_players.get(state.message.guild.id)
        if player:
            await player.process_skip(state.message.author, state.message.channel)

    @Command.register(name="playing")
    async def now_playing(self, host, state):
        '''
Returns information on the video currently playing on the bot in a given server.

Returns a default message if nothing is playing.

Usage:
g playing
        '''
        player = self.active_players.get(state.message.guild.id)
        embed = None
        if player:
            embed = player.now_playing
        if not player or not embed:
            await state.message.channel.send("*Nothing is currently playing!*")
        else:
            await state.message.channel.send(embed=embed)
