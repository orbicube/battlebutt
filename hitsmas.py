import discord
from discord.ext import commands

from random import randint, choice
import json

import checks

class Hitsmas:

    def _init_(self, bot):
        self.bot = bot

    @commands.command(aliases=['hit'])
    async def hitsmas(self, param):
        msg = ''

        await self.bot.say(msg)