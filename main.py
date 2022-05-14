
from discord.ext import commands
import redis
from datetime import datetime


bot = commands.Bot(command_prefix='!')

rdb = redis.Redis()

mmr_decay = 3
mmr_workout = 10
mmr_active = 3


@bot.command()
async def mmr(ctx):
    
    id = str(ctx.author.id)
    name = ctx.author.name

    if not rdb.sismember('musclorz-ids', id):
        new_musclor(id, name)

    update_mmr(id)

    await ctx.send(name + ' is a musclor' + \
        rdb.hget('musclor:' + id, 'mmr').decode())


@bot.command()
async def workout(ctx):
    
    id = str(ctx.author.id)
    name = ctx.author.name

    if not rdb.sismember('musclorz-ids', id):
        new_musclor(id, name)

    rdb.lpush('musclor:' + id + ':workouts', str(datetime.now().date()))
    rdb.hincrby('musclor:' + id, 'mmr', mmr_workout)

    update_mmr(id)

    await ctx.message.add_reaction('💪')


@bot.command()
async def active(ctx):

    id = str(ctx.author.id)
    name = ctx.author.name

    if not rdb.sismember('musclorz-ids', id):
        new_musclor(id, name)

    rdb.lpush('musclor:' + id + ':active-rests', str(datetime.now().date()))
    rdb.hincrby('musclor:' + id, 'mmr', mmr_active)

    update_mmr(id)

    await ctx.message.add_reaction('🧘')


def new_musclor(id, name):

    rdb.sadd('musclorz-ids', id)

    current_date_str = str(datetime.now().date())
    rdb.hset('musclor:' + id, None, None, {
        'id': id,
        'name': name,
        'start-date': current_date_str,
        'mmr': 1000,
        'last-update': current_date_str,
    })


def update_mmr(id):
    current_date = datetime.now().date()
    last_update = datetime.strptime(
        rdb.hget('musclor:' + id, 'last-update').decode(), '%Y-%m-%d'
    ).date()
    n_days = (current_date - last_update).days
    mmr = int(rdb.hget('musclor:' + id, 'mmr')) - mmr_decay * n_days
    if mmr < 0:
        mmr = 0
    rdb.hset('musclor:' + id, None, None, {
        'mmr': mmr,
        'last-update': str(current_date),
    })


with open('token') as token_file:
    token = token_file.readline()
bot.run(token)
