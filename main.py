
from discord.ext import commands
import redis
import datetime


bot = commands.Bot(command_prefix='!')

pool = redis.ConnectionPool('localhost', port=6379, db=0)


# @bot.command()
# async def test(ctx, *args):
#     await ctx.send(' '.join(args))
#     msg = ctx.message
#     await msg.add_reaction('💪')


@bot.command()
async def help(ctx):
    pass


@bot.command()
async def mmr(ctx):
    pass


@bot.command()
async def workout(ctx):
    pass


@bot.command()
async def active_rest(ctx):
    pass


with open('token') as token_file:
    token = token_file.readline()
bot.run(token)
