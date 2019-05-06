from .base import Module, Command
from discord import Embed
import math
import re


class Stattrack(Module):
    async def check(self, state):
        # multiple shorter messages take priority
        # might want to move this into a separate thread later
        strleng = len(state.content)
        if not strleng <= 0:
            strleng = math.floor(math.log(strleng) * 3)
        # for exp
        # run in executor if possible
        # n counter checks commands, exp does not
        n_counter = re.findall("(nigger|nigg\w+|nig\s+)", state.message.content)
        # if you say niggardly you are getting penalized smartass
        soft = 0
        hard = 0
        auth = state.message.author
        for bomb in n_counter:
            if bomb.endswith("r"):
                hard += 1
            else:
                soft += 1
        async with self.host.db.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.callproc("MESSAGE", (auth.id, strleng, hard, soft, state.message.guild.id))
            await conn.commit()
        return self == state.command_host

    @Command.register(name="board")
    async def guildtop(host, state):
        async with host.db.acquire() as conn:
            async with conn.cursor() as cur:
                statement = "SELECT users.username, guilds.guildexp FROM guilds JOIN users on users.user_id = guilds.user_id WHERE guild_id = %s ORDER BY guildexp DESC LIMIT 10"
                val = (state.message.guild.id)
                await cur.execute(statement, val)
                board = await cur.fetchall()
                count = len(board)
                msg = f'```glsl'
                for i in range(0, min(count, 10)):
                    msg += f'''
{i + 1}.    # {board[i][0]}
                Guild EXP: {board[i][1]}'''
                msg += "```"
                await state.message.channel.send(msg)

    @Command.register(name="rank")
    async def rank(host, state):
        msg = state.message
        if len(msg.mentions) > 0:
            target = msg.mentions[0]
            if target == host.user:
                await msg.channel.send("*beep boop*")
                return
            elif target.bot:
                await msg.channel.send("Sorry, I don't track other bots.")
                return
            userid = msg.mentions[0].id  # don't fetch all mentioned users
        else:
            userid = msg.author.id
            target = msg.author
        async with host.db.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.callproc("GLOBALINFO", (userid,))
                res = await cur.fetchone()
        print(res)
        if res is None:
            await msg.channel.send("I have no record of that user! They should probably say something first.")
            return
        if res[3] == 0:
            trivia_percent = 0  # avoid div by 0
        else:
            trivia_percent = (res[2] / res[3]) * 100
        descrip = f"""**Experience:** {res[1]} EXP\n
**Global rank:** #{res[6]}\n
**Trivia record:** {res[2]} / {res[3]} ({trivia_percent:.2f}%)\n
**Power:** {res[4]}H / {res[5]}S"""  # todo: level tracking (beyond just experience)
        response_embed = Embed(title=(target.name + "#" + target.discriminator), description=descrip, color=0x7289da)
        response_embed.set_thumbnail(url=target.avatar_url_as(static_format="png", size=512))
        await msg.channel.send(embed=response_embed)
