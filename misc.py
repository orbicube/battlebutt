import discord
from discord.ext import commands
import asyncio

from random import randint, choice
import json
import xmltodict
from datetime import datetime
import pytz
from lxml import html
from lxml.etree import tostring

import butil
import checks

class Misc:
    """Die, die, die!"""

    def __init__(self, bot):
        self.bot = bot


    @commands.command()
    async def shadow(self, ctx):

        with open('shadow.json') as f:
            data = json.load(f)

        index = randint(0, len(data['names']))
        title = data['names'][index]['title']

        song_index = randint(0, len(data['songs']))
        song = data['songs'][song_index]['url']

        msg = '{}\n{}'.format(title, song)

        await ctx.send(msg)


    async def shake8ball(self, ctx):

        with open('8ball.json') as f:
            responses = json.load(f)['responses']

        choice = randint(0, len(responses))

        msg = '{}'.format(responses[choice]['r'])

        await ctx.send(msg)


    @commands.command()
    async def goty(self, ctx):

        msg = "Congratulations to Dragon Quest XI, this Discord's communal "\
        "Game of the Year! 2018 was an extremely close-fought year with " \
        "God of War and Deltarune very close behind.\n\n" \
        "Another round of congratulations for Arcella who won the prediction "\
        "contest with 116 points! This was also a close category with four "\
        "others within 20 points.\n\n"\
        "Find the full list at https://orb.party/goty/results/"
        await ctx.send(msg)


    @commands.command(aliases=['doritos'])
    async def awards(self, ctx):
        utc = pytz.utc
        date = datetime(2019, 12, 6, 1, 30, 30, tzinfo=utc)

        out = butil.pretty_until(date)
        msg = "**" + out + "** until Gamers unite to celebrate The Game Awards!"
        await ctx.send(msg)

    
    @commands.command()
    async def classicsofgame(self, ctx):

        with open('classicsofgame.json') as f:
                data = json.load(f)

        index = randint(0, len(data['vids']))
        url = data['vids'][index]['url']

        await ctx.send(url)


def setup(bot):
    bot.add_cog(Misc(bot))