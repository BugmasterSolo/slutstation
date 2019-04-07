from discord.ext.commands import Bot
from discord import Game
from os import listdir

BOT_PREFIX = ("?", "!")

bot = Bot(command_prefix='g ', description="sorry")

def get_token():
    with open('secret_token.txt', 'r') as t:
        return t.read().strip()
    
TOKEN = get_token()

@bot.event
async def on_ready():
    print('Up and running!')
    await bot.change_premise(game=Game(name='like damn dude'))

@bot.command(name='test')
async def tester(ctx):
    await ctx.send('fuck off')

@bot.command(name='concat')
# absorbs args into a single one
# otherwise rest param absorbs word by word
async def testerTwo(ctx, *, arg):
    await ctx.send(arg)

bot.run(TOKEN)
    