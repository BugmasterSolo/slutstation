import discord

BOT_PREFIX = ("?", "!")

TOKEN = "NTY0MTgwMDkxNjc2OTE3Nzgx.XKkImg.XsPRPXS2QhQidXZKc-4fuiTC7aI"

client = Bot(command_prefix=BOT_PREFIX)

# bot object, vs. client implementation.

client.run(TOKEN)