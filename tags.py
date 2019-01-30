import discord
from discord.ext import commands
import asyncio

import json

class Tags:

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def list(self, ctx):
        with open("tags.json") as f:
            tags = json.load(f)

        msg = '```Tags:'

        for tag in sorted(tags.keys()):
            msg += '\n\t{}'.format(tag)

        msg += '```'

        await ctx.send(msg)



def setup(bot):
    bot.add_cog(Tags(bot))
