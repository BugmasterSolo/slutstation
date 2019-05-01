from .base import Module, Command
import math
import re


class Stattrack(Module):
    async def check(self, state):
        if not state.command_host and not state.message.author.bot:
            # read the message content, ensure it's None (if not, ignore, even if invalid).
            # multiple shorter messages take priority
            # might want to move this into a separate thread later
            strleng = len(state.content)
            if not strleng <= 0:
                strleng = math.floor(math.log(strleng) * 3)
            # for exp
            n_counter = re.findall("(nigg\w+|nig\s+)", state.content)
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
                    await Command.checkuser(cur, auth, state.host)  # i dont like that we have to resend the host
                    await cur.callproc("MESSAGE", (auth.id, strleng, hard, soft))
                await conn.commit()
        return False
