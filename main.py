
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
async def mmr(ctx):
    '''Your Musclor-mmr'''
    
    musclor = find_musclor(ctx)

    await ctx.send(ctx.author.name + ' you are a Musclor'
                   + rdb.hget(musclor + ':info', 'mmr').decode())
    
    
@bot.command()
async def info(ctx, mention=None):
    '''Info on mentioned @musclor (yours if no mention)'''
    
    if mention == None:
        musclor = find_musclor(ctx)
    else:
        discord_id = mention[2:-1]
        id = rdb.zscore('musclorz_ids', discord_id)
        if id == None:
            await ctx.message.add_reaction('❓')
            return -1
        else:
            musclor = 'musclor:' + str(int(id))
    
    await ctx.send(rdb.hget(musclor + ':info', 'name').decode() + ':\n'
                   + 'Musclor' + rdb.hget(musclor + ':info', 'mmr').decode() + '\n'
                   + 'Joined: ' + rdb.hget(musclor + ':info', 'start_date').decode() + '\n'
                   + 'Achievments: ' + ', '.join([achv.decode() for achv in 
                                                  rdb.zrange(musclor + ':achievments', 0, -1)]))


@bot.command()
async def musclorz(ctx):
    '''Leaderboard'''
    
    if rdb.get('n_musclorz') == None:
        await ctx.send('No musclorz yet.')
        return -1
    
    musclors = ['musclor:' + str(int(id)) for id in range(1, int(rdb.get('n_musclorz')) + 1)]
    for musclor in musclors:
        update_mmr(musclor)
    rankings = [(int(rdb.hget(musclor + ':info', 'mmr')), 
                 rdb.hget(musclor + ':info', 'name').decode()) 
                for musclor in musclors]
    
    rankings.sort(reverse=True)
    
    msg = 'Leaderboard:\n'
    for (mmr, name) in rankings:
        msg += str(mmr) + ' : ' + name + '\n'
        
    await ctx.send(msg)


@bot.command()
async def workout(ctx, week_day=None):
    '''Notify your workout/sport session'''
    
    musclor = find_musclor(ctx, week_day)
    
    n_day = day_number(musclor, determine_date(week_day))
    
    rdb.lpush(musclor + ':workouts', n_day)
    rdb.hincrby(musclor + ':info', 'mmr', MMR_WORKOUT)
    rdb.hset(musclor + ':info', 'pause', 'off')

    await ctx.message.add_reaction('💪')


@bot.command()
async def active(ctx, week_day=None):
    '''Notify your active rest (trek, short run, yoga, etc...)'''

    musclor = find_musclor(ctx, week_day)
    
    n_day = day_number(musclor, determine_date(week_day))

    rdb.lpush(musclor + ':actives', n_day)
    rdb.hincrby(musclor + ':info', 'mmr', MMR_ACTIVE)
    rdb.hset(musclor + ':info', 'pause', 'off')

    await ctx.message.add_reaction('🧘')
    
    
@bot.command()
async def pause(ctx):
    '''Stops your daily mmr decay (automatically unpause with !workout/active)'''
    
    musclor = find_musclor(ctx)
    
    rdb.hset(musclor + ':info', 'pause', 'on')
    
    await ctx.message.add_reaction('🛌')
    

@bot.command()
async def achievment(ctx, arg):
    '''Notify your latest achievment'''
    
    musclor = find_musclor(ctx)
    
    n_day = day_number(musclor, today())
    
    rdb.zadd(musclor + ':achievments', {arg: n_day})
    
    await ctx.message.add_reaction('🏆')
    

@bot.command()
async def achievments(ctx):
    '''Your achievments'''
    
    musclor = find_musclor(ctx)
    
    achievments_list = rdb.zrange(musclor + ':achievments', 0, -1, withscores=True)
    
    msg = ctx.author.name
    if len(achievments_list) == 0:
        msg += ' has no achievments yet.'
    else:
        for (achievment, n_day) in achievments_list:
            msg += '\n' + str(day_date(musclor, n_day)) + ': ' + achievment.decode()
            
    await ctx.send(msg)
    
    
def find_musclor(ctx, week_day=None):
    
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
    
    last_update = decode_date(rdb.hget(musclor + ':info', 'last_update'))
    
    n_days = (today() - last_update).days
    mmr = int(rdb.hget(musclor + ':info', 'mmr'))
    
    pause = rdb.hget(musclor + ':info', 'pause').decode() == 'on'
    if not pause:
        mmr -= MMR_DECAY * n_days
        if mmr < 0:
            mmr = 0
        
    rdb.hset(musclor + ':info', None, None, {
        'mmr': mmr,
        'last_update': str(today()),
    })


def day_number(musclor, date):
    
    start_date = decode_date(rdb.hget(musclor + ':info', 'start_date'))
    
    return (date - start_date).days


def day_date(musclor, n_day):
    
    start_date = decode_date(rdb.hget(musclor + ':info', 'start_date'))
    
    return start_date + timedelta(n_day)
    

def decode_date(date):
    return datetime.strptime(date.decode(), '%Y-%m-%d').date()


def determine_date(week_day):
    
    if week_day == None:
        return today()
    
    if week_day[-1] == ':':
        week_day = week_day[0:-1]
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
        return today()
    
    days_diff = (today().weekday() - n_weekday + 7) % 7
    
    return today() - timedelta(days_diff)


def today():
    return datetime.now().date()


with open('token') as token_file:
    token = token_file.readline()
bot.run(token)
