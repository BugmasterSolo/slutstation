from .base import Module, Command
from discord import Embed
import math
import re


class Stattrack(Module):
    CURRENCY_SYMBOL = "฿"

    async def check(self, state):
        strleng = len(state.content)
        if not strleng <= 0:
            strleng = math.floor(math.log(strleng) * 3)
        msg = state.message.content.lower()
        hard = len(re.findall("nigger", msg))
        soft = len(re.findall(r"(nigg\w*|\bnig\b)", msg)) - hard
        auth = state.message.author
        # todo: save some time by bundling commits:
        #       - create a connection from the pool.
        #       - save it, and let it collect over here.
        #       - after X seconds, commit however many messages are stacked up.
        #       - close the connection, make a new one.
        async with self.host.db.acquire() as conn:
            async with conn.cursor() as cur:
                try:
                    await cur.callproc("MESSAGE", (auth.id, strleng, hard, soft, state.message.guild.id))
                except ConnectionResetError:
                    print("Error in DB communication")
                    return self == state.command_host
            await conn.commit()
        return self == state.command_host

    @Command.register(name="board")
    async def guildtop(host, state):
        async with host.db.acquire() as conn:
            async with conn.cursor() as cur:
                # TODO: remove
                statement = "SELECT users.username, guilds.guildexp FROM guilds JOIN users on users.user_id = guilds.user_id WHERE guild_id = %s ORDER BY guildexp DESC LIMIT 10"
                val = (state.message.guild.id)
                await cur.execute(statement, val)
                board = await cur.fetchall()
                count = len(board)
                msg = f'```glsl'
                for i in range(min(count, 10)):
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
            userid = msg.mentions[0].id
        else:
            userid = msg.author.id
            target = msg.author
        async with host.db.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.callproc("GLOBALINFO", (userid, state.message.guild.id))
                res = await cur.fetchone()
        print(res)
        if res is None:
            await msg.channel.send("I have no record of that user! They should probably say something first.")
            return
        if res[3] == 0:
            trivia_percent = 0
        else:
            trivia_percent = (res[2] / res[3]) * 100
        descrip = f"""**Global rank:** #{res[6]}
**Experience:** {res[1]} EXP
*Level {res[7]} | {res[9]}/{res[8]}*\n
**Trivia record:** {res[2]} / {res[3]} ({trivia_percent:.2f}%)\n
**Power:** {res[4]}H / {res[5]}S\n
**Credits:** {res[10]} {state.command_host.CURRENCY_SYMBOL}"""
        response_embed = Embed(title=(target.name + "#" + target.discriminator), description=descrip, color=0x7289da)
        response_embed.set_thumbnail(url=target.avatar_url_as(static_format="png", size=512))
        await msg.channel.send(embed=response_embed)
