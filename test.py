from discord.ext.commands import Bot
from discord import Game
from discord import Status
import base64
import random

BOT_PREFIX = ("?", "!")

# todo:
#   - IMPLEMENT SOME COGS!!!!! will help break up the code
#   - start importing cogs to break up the bot flow
#   - figure out what exactly the bot should do
#   - store user info somewhere and fetch it (track level, xp, etc ........)
#   - asasasdadsd

bot = Bot(command_prefix='g ', description="sorry")

bot.remove_command('help')


def get_token():
    """Fetch the token from a 'secret_token.txt' file.

    File is stored in the same folder as the script.
    """
    with open('secret_token.txt', 'r') as t:
        return t.read().strip()


TOKEN = get_token()


@bot.event
async def on_ready():
    """Notifies the user that the bot is running."""
    print('Up and running!')
    await bot.change_presence(status=Status.online, activity=Game("mike craft"))


# wrapper: "packages" the command in a way that allows it to keep eyes out for
#          the name,
#          then passes in the context when necessary.
@bot.command(name='test')
# commands accept a context, and the message is sent back thru the context.
async def tester(ctx):
    """Simple test command."""
    await ctx.send('fuck off')

@bot.command
async def help(ctx):
    await ctx.send('to be decided')


@bot.command(name='concat')
# absorbs args into a single one
# otherwise rest param absorbs word by word
# **kwargs at the end
async def testerTwo(ctx, *, arg):
    """Another simple test command."""
    await ctx.send(arg)

# best way to log the number of coin flips in a given server?
# this is getting into storing database files or accessing one,
# i'll look into that soon.
@bot.command
async def coinflip(ctx):
    rand_event = ("the coin shattered and the shards deposited in your eyes",
                  "The coin landed on its side!",
                  "What coin? I don't have a coin.",
                  "THIS MESSAGE IS AN ERROR. PLEASE NOTIFY THE DEVELOPER.",
                  "please do not ask these questions of me")
    status = random.random()
    if status > 0.50005:
        await ctx.send("You flipped heads!")
    elif status < 0.001:
        await ctx.send(rand_event[random.randint(0, len(rand_event) - 1)])
    else:
        await ctx.send("You flipped tails!")


@bot.command(name="pushup")
async def pushup(ctx, *args):
    try:
        msg = ctx.message
        num = float(args[0])
        if num % 1 == 0:
            num = int(num)
        if msg.author != bot.user:
            await msg.channel.send("that's cool but i can do " +
                                   str(num + 1) + " pushups")
    except Exception as e:
        print("passed non-number")
        await msg.channel.send("that's cool but i can do " +
                               str(base64.b64encode(msg.content.encode())) +
                               " pushups")




@bot.command(name="users")
async def users(ctx):
    await ctx.message.channel.send(f"""# of users: {ctx.message.guild.member_count}""")


@bot.event
# i'd imagine this wrapper takes the function name and attaches it to an event
# based on.
# the event keeps track of the API, then routes it back to here
async def on_guild_join(guild):
    """Send message when joining a server for the first time."""
    # this event accepts a guild only.
    print("Invited to {}: ID {}".format(guild.name, guild.id))
    open_channel = find_channel(guild)
    if open_channel is None:
        await open_channel.send("Thanks for the invite :)")
    else:
        print("could not post join message.")


def find_channel(guild):
    """Find available channel in server."""
    for c in guild.text_channels:
        if c.permissions_for(guild.me).send_messages:
            return c
    return None


bot.run(TOKEN)
