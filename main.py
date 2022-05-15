
from discord.ext import commands
import redis
from datetime import datetime, timedelta


bot = commands.Bot(command_prefix='!')

rdb = redis.Redis()

MMR_BASE = 1000
MMR_DECAY = 3
MMR_WORKOUT = 10
MMR_ACTIVE = 3


@bot.command()
async def test(ctx, week_day=None):
    print(week_day)


@bot.command()
async def mmr(ctx):
    
    musclor = find_musclor(ctx, None)

    await ctx.send(ctx.author.name + " you're a musclor" + \
        rdb.hget(musclor + ':info', 'mmr').decode())


@bot.command()
async def workout(ctx, week_day=None):
    
    musclor = find_musclor(ctx, week_day)
    
    n_day = day_number(musclor, determine_date(week_day))
    
    rdb.lpush(musclor + ':workouts', n_day)
    rdb.hincrby(musclor + ':info', 'mmr', MMR_WORKOUT)
    rdb.hset(musclor + ':info', 'pause', 'off')

    await ctx.message.add_reaction('💪')


@bot.command()
async def active(ctx, week_day=None):

    musclor = find_musclor(ctx, week_day)
    
    n_day = day_number(musclor, determine_date(week_day))

    rdb.lpush(musclor + ':actives', n_day)
    rdb.hincrby(musclor + ':info', 'mmr', MMR_ACTIVE)
    rdb.hset(musclor + ':info', 'pause', 'off')

    await ctx.message.add_reaction('🧘')
    
    
@bot.command()
async def pause(ctx):
    
    musclor = find_musclor(ctx, None)
    
    rdb.hset(musclor + ':info', 'pause', 'on')
    
    await ctx.message.add_reaction('🛌')
    

@bot.command()
async def achievment(ctx, arg):
    
    musclor = find_musclor(ctx, None)
    
    rdb.lpush(musclor + ':achievments', arg)
    
    await ctx.message.add_reaction('🏆')
    

@bot.command()
async def achievments(ctx):
    
    musclor = find_musclor(ctx, None)
    
    achievments_list = rdb.lrange(musclor + ':achievments', 0, -1)
    
    if len(achievments_list) == 0:
        msg = ctx.author.name + ' has no achievments yet'
    else:
        msg = ctx.author.name + ' has the following achievments: ' \
            + ', '.join([achv.decode() for achv in achievments_list])
            
    await ctx.send(msg)
    
    
def find_musclor(ctx, week_day):
    
    discord_id = ctx.author.id
    
    id = rdb.zscore('musclorz_ids', discord_id)
    
    if id == None:
        musclor = new_musclor(discord_id, ctx.author.name, week_day)
    else:
        musclor = 'musclor:' + str(int(id))
        
    update_mmr(musclor)
        
    return musclor


def new_musclor(discord_id, name, week_day):
    
    id = rdb.incr('n_musclorz')

    rdb.zadd('musclorz_ids', {discord_id: id})
    
    musclor = 'musclor:' + str(id)

    date_str = str(determine_date(week_day))
    rdb.hset(musclor + ':info', None, None, {
        'id': id,
        'discord_id': discord_id,
        'name': name,
        'start_date': date_str,
        'mmr': MMR_BASE,
        'last_update': date_str,
        'pause': 'off',
    })
    
    return musclor


def update_mmr(musclor):
    
    current_date = datetime.now().date()
    last_update = decode_date(rdb.hget(musclor + ':info', 'last_update'))
    
    n_days = (current_date - last_update).days
    mmr = int(rdb.hget(musclor + ':info', 'mmr'))
    
    pause = rdb.hget(musclor + ':info', 'pause').decode() == 'on'
    if not pause:
        mmr -= MMR_DECAY * n_days
        if mmr < 0:
            mmr = 0
        
    rdb.hset(musclor + ':info', None, None, {
        'mmr': mmr,
        'last_update': str(current_date),
    })


def day_number(musclor, date):
    
    start_date = decode_date(rdb.hget(musclor + ':info', 'start_date'))
    
    return (date - start_date).days
    

def decode_date(date):
    return datetime.strptime(date.decode(), '%Y-%m-%d').date()


def determine_date(week_day):
    
    today = datetime.now().date()
    
    if week_day == None:
        return today
    
    week_day = week_day.lower()
    
    if week_day == 'lundi' or week_day == 'monday':
        n_weekday = 0
    elif week_day == 'mardi' or week_day == 'tuesday':
        n_weekday = 1
    elif week_day == 'mercredi' or week_day == 'wednesday':
        n_weekday = 2
    elif week_day == 'jeudi' or week_day == 'thursday':
        n_weekday = 3
    elif week_day == 'vendredi' or week_day == 'friday':
        n_weekday = 4
    elif week_day == 'samedi' or week_day == 'saturday':
        n_weekday = 5
    elif week_day == 'dimanche' or week_day == 'sunday':
        n_weekday = 6
    else:
        return today
    
    days_diff = (today.weekday() - n_weekday + 7) % 7
    
    return today - timedelta(days_diff)


with open('token') as token_file:
    token = token_file.readline()
bot.run(token)
