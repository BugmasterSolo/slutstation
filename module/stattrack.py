from .base import Module, Command
import math
import re


class Stattrack(Module):
    async def check(self, state):
        if not state.command_host:
            # read the message content, ensure it's None (if not, ignore, even if invalid).
            # multiple shorter messages take priority
            # might want to move this into a separate thread later
            strleng = math.floor(math.log(len(state.content)) * 3)
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
                    await Command.checkuser(cur, auth)
                    await cur.callproc("MESSAGE", (auth.id, strleng, hard, soft))
                await conn.commit()
