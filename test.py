from discord.ext.commands import Bot
from discord import Game
from discord import Status
from os import listdir

BOT_PREFIX = ("?", "!")

# todo:
#   - start importing cogs to break up the bot flow
#   - figure out what exactly the bot should do
#   - store user info somewhere and fetch it (track level, xp, etc ........)
#   - asasasdadsd

bot = Bot(command_prefix='g ', description="sorry")

def get_token():
    with open('secret_token.txt', 'r') as t:
        return t.read().strip()

TOKEN = get_token()

@bot.event
async def on_ready():
    print('Up and running!')
    await bot.change_presence(status=Status.online, activity=Game("mike craft"))

# wrapper: "packages" the command in a way that allows it to keep eyes out for the name,
#          then passes in the context when necessary.
@bot.command(name='test')
# commands accept a context, and the message is sent back thru the context.
async def tester(ctx):
    await ctx.send('fuck off')

@bot.command(name='concat')
# absorbs args into a single one
# otherwise rest param absorbs word by word
# **kwargs at the end
async def testerTwo(ctx, *, arg):
    await ctx.send(arg)

@bot.event
# i'd imagine this wrapper takes the function name and attaches it to an event based on.
# the event keeps track of the API, then routes it back to here
async def on_guild_join(guild):
    # this event accepts a guild only.
    print("Invited to {}: ID {}".format(guild.name, guild.id))
    open_channel = find_channel(guild)
    if not open_channel == None:
        await open_channel.send("Thanks for the invite :)")
    else:
        print("could not post join message.")

def find_channel(guild):
    for c in guild.text_channels:
        if c.permissions_for(guild.me).send_messages:
            return c;
    return None;



bot.run(TOKEN)
