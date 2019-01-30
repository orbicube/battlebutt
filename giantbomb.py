import discord
from discord.ext import commands
import asyncio
import aiohttp

import json
import pytz
from datetime import datetime, timedelta
from random import randint
import xmltodict

import butil

import logging
logging.getLogger()


class GiantBomb:

    headers = {
        'User-Agent': 'battlebutt/1.0 (github.com/orbicube/battlebutt)',
        'Host': 'www.giantbomb.com' }
    gb_api_key = ''
    post_channels = [
        122087203760242692,
        143562235740946432
    ]


    def __init__(self, bot):
        self.bot = bot
        with open('credentials.json') as f:
            self.gb_api_key = json.load(f)['giantbomb']


        self.upcoming_task = self.bot.loop.create_task(self.upcoming_task())
        self.livestream_task = self.bot.loop.create_task(self.livestream_task())
        self.videos_task = self.bot.loop.create_task(self.videos_task())
        self.reviews_task = self.bot.loop.create_task(self.reviews_task())
        self.playing_task = self.bot.loop.create_task(self.playing_task())


    async def upcoming_task(self):
        await self.bot.wait_until_ready()

        while not self.bot.is_closed():

            await self.check_upcoming()
            await asyncio.sleep(45)

    async def livestream_task(self):
        await self.bot.wait_until_ready()

        while not self.bot.is_closed():

            await self.check_live()
            await asyncio.sleep(45)

    async def videos_task(self):
        await self.bot.wait_until_ready()

        while not self.bot.is_closed():
            await self.check_videos()
            await asyncio.sleep(45)

    async def reviews_task(self):
        await self.bot.wait_until_ready()

        while not self.bot.is_closed():
            await self.check_reviews()
            await asyncio.sleep(60)

    async def playing_task(self):
        await self.bot.wait_until_ready()

        while not self.bot.is_closed():
            await self.update_game()
            await asyncio.sleep(600)


    async def check_videos(self):

        url = 'http://www.giantbomb.com/api/videos/'

        print("\nChecking GB videos")

        p = {
            'api_key': self.gb_api_key,
            'format': 'json',
            'limit': '3'
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self.headers, params=p) as r:
                    js = await r.json()
        except:
            return
        vids = js['results']

        with open('gb_videos.json') as f:
            j = json.load(f)

        for v in vids:
            if v['id'] == j['latest_vid']:
                break

            msg = "New {prem}Giant Bomb video!\n{url}".format(
                prem='Premium ' if v['video_type'] == 'Premium' else '',
                url=v['site_detail_url']
            )

            embed = discord.Embed(
                title=v['name'],
                description="{}\n\nLength: {}".format(
                    v['deck'],
                    butil.pretty_seconds(v['length_seconds'])),
                url=v['site_detail_url']
            )
            embed.set_image(url=v['image']['super_url'])

            for c in self.post_channels:
                chan = self.bot.get_channel(c)
                await chan.send(msg, embed=embed)


        j['latest_vid'] = vids[0]['id']
        
        with open('gb_videos.json', 'w') as f:
            json.dump(j, f)


    async def check_reviews(self):
        
        url = 'https://www.giantbomb.com/api/reviews/'

        p = {
            'api_key': self.gb_api_key,
            'format': 'json',
            'limit': '3'
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self.headers, params=p) as r:
                    js = await r.json()
        except:
            return
        reviews = js['results']

        with open('gb_reviews.json') as f:
            j = json.load(f)

        for r in reviews:
            if r['id'] == j['latest_review']:
                break

            score = ''
            for x in range(int(r['score'])):
                score += '★'
            if int(r['score']) < 5:
                for y in range((5 - int(r['score']))):
                    score += '☆'

            msg= " New Giant Bomb review!"\
            "\n\n**{game}** ({platforms}) received {score} from {author}."\
            "\n{url}".format(
                game=r['game']['name'],
                platforms=r['platforms'],
                score=score,
                author=r['reviewer'],
                url=r['site_detail_url']
            )

            for c in self.post_channels:
                chan = self.bot.get_channel(c)
                await chan.send(msg, embed=embed)

        j['latest_review'] = reviews[0]['id']

        with open('gb_reviews.json', 'w') as f:
            json.dump(j, f)


    async def check_podcasts(self, post_test):

        curr_time = datetime.now(pytz.timezone('US/Pacific'))
        day = curr_time.strftime("%A")
        month = curr_time.strftime("%b")
        date = int(curr_time.strftime("%d"))
        hour = int(curr_time.strftime("%H"))

        with open('podcasts.json') as f:
            j = json.load(f)

        # Bombcast
        if day == "Tuesday" and hour > 11 and j['bombcast']['posted'] == False:
            url = j['bombcast']['url']

            print('Bombcast Check')

            async with aiohttp.get(url, headers=self.headers) as r:
                feed = await r.text()









    async def check_upcoming(self):

        url = 'https://www.giantbomb.com/upcoming_json'

        with open('gb_upcoming.json') as f:
            j = json.load(f)

        print("\nChecking upcoming GB content")

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self.headers) as r:
                    js = await r.json()
        except:
            return
        upcoming = js['upcoming']
        new_upcoming = []

        for u in upcoming:
            if u not in j['upcoming']:
                new_upcoming.append(u)

        j['upcoming'] = upcoming

        with open('gb_upcoming.json', 'w') as f:
            json.dump(j, f)

        msg = ''
        if new_upcoming:
            tz = pytz.timezone("America/Los_Angeles")

            for u in new_upcoming:
                msg = 'New content coming up on Giant Bomb!'
                naive = datetime.strptime(u['date'], "%b %d, %Y %I:%M %p")
                sf_dt = tz.localize(naive)
                utc_dt = sf_dt.astimezone(pytz.utc)

                until = butil.pretty_until(utc_dt)

                msg += '\n\n{title}\n\t{prem}{type}{until}'.format(
                    prem='Premium ' if u['premium'] else '',
                    type=u['type'],
                    title=u['title'],
                    until=' in {}'.format(until) if until else '')

                if u['image']:
                    embed = discord.Embed()
                    embed.set_image(url='https://'+u['image'].replace(' ','%20'))

                    for c in self.post_channels:
                        chan = self.bot.get_channel(c)
                        await chan.send(msg, embed=embed)
                else:
                    for c in self.post_channels:
                        chan = self.bot.get_channel(c)
                        await chan.send(msg, embed=embed)


    @commands.command()
    async def live(self, ctx):

        msg = 'Current live shows:'

        with open('gb_live.json') as f:
            j = json.load(f)

        for c in j['chats']:
            msg += '\n\n{title}\n\t{deck}'.format(
                title=c['title'],
                deck=c['deck'])

        if '\n' not in msg:
            msg += '\n\nNone!'

        await ctx.send(msg)


    async def check_live(self):

        url = 'http://www.giantbomb.com/api/chats/'

        with open ('gb_live.json') as f:
            j = json.load(f)

        print('\nGetting active live shows from GB')

        p = {
            'api_key': self.gb_api_key,
            'format': 'json'
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self.headers, params=p) as r:
                    js = await r.json()
        except:
            return
        chats = js['results']
        new_chats = []

        for c in chats:
            if c not in j['chats']:
                new_chats.append(c)

        j['chats'] = chats

        with open('gb_live.json', 'w') as f:
            json.dump(j, f)

        chat_msg = ''
        if new_chats:
            for c in new_chats:
                chat_msg = 'New Giant Bomb live show!\n{}'.format(
                    c['site_detail_url']
                )

                embed = discord.Embed(
                    title=c['title'],
                    url=c['site_detail_url'],
                    description=c['deck']
                )
                embed.set_thumbnail(url=c['image']['medium_url'])
            for c in self.post_channels:
                chan = self.bot.get_channel(c)
                await chan.send(chat_msg, embed=embed)


    @commands.command()
    async def upcoming(self, ctx):

        msg = 'Coming up on Giant Bomb:'

        with open('gb_upcoming.json') as f:
            upcoming = json.load(f)['upcoming']

        tz = pytz.timezone("America/Los_Angeles")

        for u in upcoming:
            naive = datetime.strptime(u['date'], "%b %d, %Y %I:%M %p")
            sf_dt = tz.localize(naive)
            utc_dt = sf_dt.astimezone(pytz.utc)

            until_msg = butil.pretty_until(utc_dt)

            msg += '\n\n{title}\n\t{prem}{type}{until}'.format(
                prem='Premium ' if u['premium'] else '',
                type=u['type'],
                title=u['title'],
                until=' in {}'.format(until_msg) if until_msg else '')

        if '\n' not in msg:
            msg += '\n\nNothing!'

        await ctx.send(msg)

    @commands.command()
    async def playing(self, ctx):

        with open('gb_playing.json') as f:
            j = json.load(f)

        # Check for platforms to list
        plats = j['game']['platforms']
        out_plats = ''
        if plats:
            print('\nFormatting platforms')
            num_plats = len(plats)
            remainder = 0
            if num_plats > 4:
                print('More than four platforms')
                remainder = num_plats - 4
                num_plats = 4

            select_plats = []
            for i in range(num_plats):
                select_plats.append(
                    plats.pop(randint(0, len(plats)-1))['name']
                )

            out_plats = 'Platform{s}: {out}{plus}'.format(
                s = 's' if len(select_plats) > 1 else '',
                out = ', '.join(select_plats),
                plus = ' + {}'.format(remainder) if remainder > 0 else '')

        # Compose output
        msg = j['game']['url']
        embed = discord.Embed(
            title=j['game']['name'],
            url=j['game']['url'],
            description="{plats}{deck}".format(
                plats='{}\n\n'.format(out_plats) if out_plats else '',
                deck=j['game']['deck'] if j['game']['deck'] else ''))

        # If it has an image, upload as image w/ caption
        if j['game']['image']:
            embed.set_image(
                url=j['game']['image'])

        await ctx.send(msg, embed=embed)

        await self.bot.get_cog('Abe').handle_urls(
            ['{}'.format(j['game']['url'])],
            ctx.message,
            ctx)


    @commands.command(hidden=True)
    async def update_game_list(self):

        p = {
            'api_key': self.gb_api_key,
            'sort': 'id:desc',
            'limit': '1',
            'field_list': 'id',
            'format': 'json'
        }
        url = "http://www.giantbomb.com/api/games/"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self.headers, params=p) as r:
                    with open('gb_playing.json') as f:
                        j = json.load(f)

                j['game']['latest'] = await r.json()['results'][0]['id']

                with open('gb_playing.json', 'w') as f:
                    json.dump(j, f)
        except:
            return


    async def update_game(self):
        test_chan = self.bot.get_channel(402750968099373057)
        # Grab maximum possible game ID from storage
        with open('gb_playing.json') as f:
            max_game_id = int(json.load(f)['game']['latest'])

        # Pick a random number between the 1 and the cap
        game_id = randint(1, max_game_id)
        print('\nTrying to grab game {} from GB wiki'.format(game_id))

        p = {
            'api_key': self.gb_api_key,
            'field_list': 'name,site_detail_url,image,platforms,deck',
            'format': 'json'
        }

        # Grab it
        url = 'http://www.giantbomb.com/api/game/3030-{}/'.format(game_id)
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self.headers, params=p) as r:
                    js = await r.json()
        except:
            return

        # Make sure the game with that ID actually exists in GB's database!
        if js['error'] != 'OK':
            print('Game {} does not exist in GB\'s wiki, trying again'.format(
                game_id))
            await test_chan.send(
                "{} not found, trying again".format(game_id))
            await self.update_game()
        else:
            print('Game {} exists in GB\'s wiki'.format(game_id))

            await self.bot.change_presence()

            game = js['results']

            with open('gb_playing.json') as f:
                j = json.load(f)

            # Update data
            j['game']['name'] = game['name']

            if game['image']:
                j['game']['image'] = game['image']['super_url']
            else:
                j['game']['image'] = ''

            j['game']['url'] = game['site_detail_url']

            j['game']['platforms'] = game['platforms']

            j['game']['deck'] = game['deck']

            with open('gb_playing.json', 'w') as f:
                json.dump(j, f)

            await self.bot.change_presence(activity=discord.Game(name=game['name']))
            await test_chan.send(game['name'])




def setup(bot):
    bot.add_cog(GiantBomb(bot))
