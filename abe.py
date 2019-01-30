import discord
from discord.ext import commands
import asyncio

import re
import json
from urllib.parse import urlparse

import butil

class Abe:

    def __init__(self, bot):
        self.bot = bot


    @commands.command()
    async def abe(self, ctx):

        with open('url_history.json') as f:
            data = json.load(f)

        msg = '{} Abes to date (last one {}).'.format(
            data['total'],
            butil.pretty_date(data['epoch'])
        )

        await ctx.send(msg)


    async def handle_urls(self, urls, message, ctx):

        if message.author.id == 186882370274721793:
            return
        if message.channel.id == 230026389015756800:
        	return
        if message.channel.id == 499632759040507904:
            return
        if message.channel.id == 454317864326004736:
            return

        self.purge_urls()
        for u in urls:
            u = u.lower()
            if "twitter.com" in u:
                u = self.handle_twitter(u, message)
            await self.check_url(u, message, ctx)
            self.add_url(u, message)


    def handle_twitter(self, url, message):

        test_channel = discord.utils.get(
            self.bot.get_all_channels(),
            id='143562235740946432'
        )

        tw_url = urlparse(url).path
        tw_id = "tw/" + tw_url.rstrip('/').rsplit('/', 1)[1]

        return tw_id


    def add_url(self, url, message):
        
        d = {
            'id': message.author.id,
            'name': message.author.display_name,
            'url': url,
            'time': butil.now_epoch(),
            'guild': message.guild.id,
            'channel': message.channel.id
        }
        with open('url_history.json') as f:
            j = json.load(f)

        j['urls'].append(d)

        with open('url_history.json', 'w') as f:
            json.dump(j, f)


    def purge_urls(self):

        with open('url_history.json') as f:
            j = json.load(f)

        new_list = []

        for i in j['urls']:
            if (butil.now_epoch() - i['time']) < (3600*24):
                new_list.append(i)
            else:
                print('Purged {}'.format(i['url']))

        j['urls'] = new_list

        with open('url_history.json', 'w') as f:
            json.dump(j, f)


    async def check_url(self, url, message, ctx):

        with open('url_history.json') as f:
            j = json.load(f)

        matches = [
            m for m in j['urls']
            if m['url'] == url
            and m['guild'] == message.guild.id
            and m['channel'] == message.channel.id
        ]


        if matches and matches[0]['id'] != message.author.id:
            j['epoch'] = butil.now_epoch()
            j['total'] += 1

            with open('url_history.json', 'w') as f:
                json.dump(j, f)

            names = ', '.join(set([
                m['name'] for m in matches
            ]))
            if ', ' in names:
                (n_l, comma, n_r) = names.rpartition(', ')
                names = ' and '.join((n_l, n_r))

            earliest = butil.pretty_date(min(m['time'] for m in matches))

            msg = '(linked by {linkers}, first linked {earliest})'.format(
                linkers=names,
                earliest=earliest)

            abe_count = len(matches) - 1
            if abe_count > 5:
                abe_count = "5"
            else:
                abe_count = str(abe_count)
            await ctx.send(
                file=discord.File("abe{}.jpg".format(abe_count)),
                content=msg)

def setup(bot):
    bot.add_cog(Abe(bot))
