from .base import Module, Command
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
                val = (state.message.channel.id)
                await cur.execute(statement, val)
                board = await cur.fetchall()
                print(board)  # format properly (javascript yielded moderate results, check bitch too)
        pass
