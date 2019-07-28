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
        hard = len(re.findall("nigger", msg))  # bro its cool i bought a pass
        soft = len(re.findall(r"(nigg\w*|\bnig\b)", msg)) - hard
        auth = state.message.author
        # TODO: save some time by bundling commits:
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
                    return state.command_host == self
            await conn.commit()
        return state.command_host == self

    @Command.register(name="board")
    async def guildtop(self, host, state):
        '''
See who's killing it locally.

Usage:
g board
        '''
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

    @Command.register(name="servertip")
    async def servertip(self, host, state):
        '''
Pay forward a chunk of your credits towards your currently active server.
        '''
        value = 0
        try:
            value = int(state.content)
        except ValueError:
            return
        async with host.db.acquire() as conn:
            async with conn.cursor() as cur:
                if not await host.spendcredits(cur, state.message.author.id, value):
                    await state.message.channel.send("You do not have enough credits to tip that amount!")
                    return
                await cur.callproc("SEND_TIP", (state.message.guild.id, value))
            await conn.commit()
        await state.message.channel.send(f"Successfully added {value} credits to the server tip jar!")

    @Command.register(name="rank")
    async def rank(self, host, state):
        '''
Displays an embedded summary of your history as a user, or the history of another user.

Usage:
g rank <user mention>
        '''
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
**Credits:** {res[10]} {self.CURRENCY_SYMBOL}"""
        response_embed = Embed(title=(target.name + "#" + target.discriminator), description=descrip, color=0x7289da)
        response_embed.set_thumbnail(url=target.avatar_url_as(static_format="png", size=512))
        await msg.channel.send(embed=response_embed)
