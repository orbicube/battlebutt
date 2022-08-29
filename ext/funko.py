import discord
from discord.ext import commands
from discord import app_commands

from random import randint, choice, choices
from datetime import datetime

import httpx

class Funko(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command()
    async def funko(self, ctx):
        """ Posts a random Funko Pop figure """

        url = "https://api.funko.com/api/search/terms"
        headers = {
            "User-Agent": "Popspedia/1 CFNetwork/1325.0.1 Darwin/21.0.0",
            "Content-Type": "application/json"        
        }

        # API cannot paginate beyond 10k results so we need to filter.
        # Search results contain metadata on matching items, which we can use
        # to pick a random year with proper weighting to filter results.

        data = {
            "type": "catalog",
            "page": "1",
            "pageCount": "10",
            "productLines": ["blox", "pop! 8-bit", "pop! mask", "pop! pez", 
                "pop! moments", "pop! rides", "pop! town", "pop! trains",
                "pop! vinyl", "vinyl cubed"]
        }

        async with httpx.AsyncClient() as client:
            r = await client.post(url, headers=headers, json=data)
            results = r.json()

            # Randomly pick a year based on weighting from item counts
            years = [year['key'] for year in results['attributes']['releaseDate']]
            counts = [year['count'] for year in results['attributes']['releaseDate']]
            year = choices(years, counts)[0]

            # Get that year's associated count
            year_count = counts[years.index(year)]

            # Grab random page from that 
            data['page'] = str(randint(1, (year_count / 10) + 1))
            data['releaseDate'] = [year]

            r = await client.post(url, headers=headers, json=data)
            results = r.json()

        funko = choice(results['hits'])

        await ctx.send(funko['title'])



async def setup(bot):
    await bot.add_cog(Funko(bot))