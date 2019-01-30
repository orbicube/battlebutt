import discord
from discord.ext import commands
import asyncio

import requests
from datetime import datetime, timedelta
import json

import butil

class Stats:

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def lookup(self, s_id : str):

        if not s_id:
            await self.bot.say("Give me a Steam game ID.")
            await self.bot.say('{} players'.format(
                str(self.get_steam_players(s_id))))


    @commands.command(aliases=['lows'])
    async def low(self):

        with open('bb_stats.json') as f:
            data = json.load(f)

        msg = 'Here\'s the all-time lows:'
        
        for i in range(0, len(data)):
            if data[i]['dead'] == 'no':
                msg += '\n{} - {} ({})'.format(
                    data[i]['name'],
                    data[i]['stats']['low'],
                    butil.pretty_date(data[i]['epoch']['low'])
                )

        await self.bot.say(msg)


    @commands.command(aliases=['highs'])
    async def high(self):

        with open('bb_stats.json') as f:
            data = json.load(f)

        msg = 'Here\'s the recorded highs:'

        for i in range(0, len(data)):
            if data[i]['dead'] == 'no':
                msg += '\n{} - {} ({})'.format(
                    data[i]['name'],
                    data[i]['stats']['high'],
                    butil.pretty_date(data[i]['epoch']['high'])
                )

        await self.bot.say(msg)


    @commands.command()
    async def stats(self):

        with open('bb_stats.json') as f:
            data = json.load(f)

        reg_title = 'Current Stats:\n'
        reg = []
        clicker_title = '\n\nBattlefield Borough:\n'
        clicker = []

        for i in range(0, len(data)):
            if data[i]['dead'] == 'no':
                if data[i]['type'] == 'Twitch':
                    curr = self.get_twitch_viewers(data[i]['id'])

                elif data[i]['type'] == 'Steam' or data[i]['type'] == 'Clicker':
                    curr = self.get_steam_players(data[i]['id'])
                    if curr == 0:
                        msg = 'Steam API is down currrently.'
                        await self.bot.say(msg)
                        return

                elif data[i]['type'] == 'Manygolf':
                    curr = self.get_manygolf_players()

                elif data[i]['type'] == 'bf1':
                    curr = self.get_bf1_players(data[i]['id'])

                comp = self.compare(
                    curr,
                    data[i]['prev'],
                    data[i]['stats']['low'],
                    data[i]['stats']['high']
                )

                if curr == 69:
                    comp = '**NICE** ' + comp[1:]

                if 'LOW!' in comp:
                    data[i]['stats']['low'] = curr
                    data[i]['epoch']['low'] = butil.now_epoch()
                elif 'HIGH!' in comp:
                    data[i]['stats']['high'] = curr
                    data[i]['epoch']['high'] = butil.now_epoch()
                
                data[i]['prev'] = curr

                msg = '{} - {}{}'.format(
                    data[i]['name'],
                    curr,
                    comp
                )

                if data[i]['type'] == 'bf1':
                    clicker.append((msg, curr))
                else:
                    reg.append((msg, curr))

        with open('bb_stats.json', 'w') as f:
            json.dump(data, f)

        reg_msg = '\n'.join(
            [ s[0] for s in sorted(reg, key=lambda x: x[1], reverse = True) ]
        )
        clicker_msg = '\n'.join(
            [ s[0] for s in sorted(clicker, key=lambda x: x[1], reverse = True) ]
        )
        clicker_msg += '\nTotal - {}'.format(
            sum(c for name, c in clicker)
        )

        await self.bot.say(reg_title+reg_msg+clicker_title+clicker_msg)


    @commands.command(aliases=['retire'])
    async def retired(self):

        with open('bb_stats.json') as f:
            data = json.load(f)

        msg = 'Retirement Village:'

        for i in range(0, len(data)):
            if data[i]['dead'] == 'retired':
                msg += '\n{} retired with a high of {} and a low of {}.'.format(
                    data[i]['name'],
                    data[i]['stats']['high'],
                    data[i]['stats']['low']
                )

        await self.bot.say(msg)


    @commands.command(aliases=['rip'])
    async def graveyard(self):
        
        with open('bb_stats.json') as f:
            data = json.load(f)

        msg = 'Graveyard:'

        for i in range(0, len(data)):
            if data[i]['dead'] == 'yes':
                msg += '\nRIP {} ({}-{}). It had a peak of {}.'.format(
                    data[i]['name'],
                    data[i]['release'],
                    datetime.utcfromtimestamp(
                        data[i]['epoch']['low']
                    ).strftime("%Y"),
                    data[i]['stats']['high']

                )

        await self.bot.say(msg)


    def get_bf1_players(self, platform):

        await with aiohttp.get(
            "http://api.bf1stats.com/api/onlinePlayers") as r:
        stats = r.json()

        return int(stats[platform]['count'])


    def get_manygolf_players(self):

        await with aiohttp.get(
            'https://manygolf.club/server/player-count') as r:

        return int(r.text)


    def get_steam_players(self, app_id):

        r = requests.get(
            'https://api.steampowered.com/ISteamUserStats/' \
            'GetNumberOfCurrentPlayers/v1/',
            params = {
                'key': 'yyyxxxzzz',
                'format': 'json',
                'appid': app_id
            }
        )

        players = r.json()['response']['player_count']

        return int(players)


    def get_twitch_viewers(self, title):

        with open('credentials.json') as f:
            cid = json.load(f)['twitch']

        twitch_headers = {
            'Accept': 'application/vnd.twitchtv.3+json',
            'Client-ID': cid
        }

        r = requests.get(
            'https://api.twitch.tv/kraken/search/games',
            params = {
                'q': title,
                'type': 'suggest',
                'live': 'true'
            },
            headers = twitch_headers
        )

        games = r.json()['games']

        viewers = 0
        for i in games:
            if i['name'] == title:
                viewers = i['popularity']

        return int(viewers)


    def compare(self, curr, prev, low, high):

        if prev == 0:
            return ''

        diff = 0
        sign = ''

        if curr != prev:
            diff = (float(curr) / float(prev)) * 100

            if diff > 100:
                diff = diff - 100

                if curr > int(high):
                    sign = '**NEW HIGH!** +'
                else:
                    sign = '+'

            else:
                diff = 100 - diff

                if curr < int(low):
                    sign = '**NEW LOW!** -'
                else:
                    sign = '-'


            return ' ({0}{1}%)'.format(
                sign,
                str(round(diff, 1) if diff % 1 else int(diff))
            )

        else:
            return ""


def setup(bot):
    bot.add_cog(Stats(bot))
