import discord
from discord.ext import commands

from random import randint, choice, choices
from datetime import datetime

class Funko(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command()
    async def funko(self, ctx):
        """ Posts a random Funko Pop figure """

        # Defer in case HTTP requests take too long
        await ctx.defer()

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

        r = await self.bot.http_client.post(url, headers=headers, json=data)
        results = r.json()

        # Randomly pick a year based on weighting from item counts.
        years = [year['key'] for year in results['attributes']['releaseDate']]
        counts = [year['count'] for year in results['attributes']['releaseDate']]
        year = choices(years, counts)[0]

        # Get that year's associated count.
        year_count = counts[years.index(year)]

        # 10 items per page so divide item count by 10 and round up.
        data['page'] = str(randint(1, (year_count / 10).__ceil__()))
        data['releaseDate'] = [year]

        r = await self.bot.http_client.post(url, headers=headers, json=data)
        results = r.json()

        funko = choice(results['hits'])
        embed = discord.Embed(
            title = funko['title'],
            color = 5723991)

        # Convert timestamp to human-readable string ("Year"/"Month Xth, Year")
        release_date = datetime.strptime(
            funko['releaseDate'].split('T')[0],
            "%Y-%m-%d")
        if release_date.month == 1 and release_date.day == 1:
            release_value = release_date.year
        else:
            day = release_date.day
            if 4 <= day <= 20 or 24 <= day <= 30:
                suffix = "th"
            else:
                suffix = ["st", "nd", "rd"][day % 10 - 1]
            release_value = "{} {}{}, {}".format(
                release_date.strftime("%B"),
                day, suffix,
                release_date.strftime("%Y"))
        embed.add_field(
            name = "Release Date",
            value = release_value,
            inline = True)

        # Some items do not have this field.
        if "marketValue" in funko.keys():
            embed.add_field(
                name = "Value",
                value = f"${funko['marketValue']:n}",
                inline = True)

        embed.set_footer(text = funko['licenses'][0])

        # More recent items may have multiple images provided.
        # The first is usually the box while the second is the raw figure.
        if len(funko['additionalImages']) > 1:
            embed.set_image(url=f"https://api.funko.com{funko['additionalImages'][1]}")
            embed.set_thumbnail(url=f"https://api.funko.com{funko['additionalImages'][0]}")
        else:
            embed.set_image(url=f"https://api.funko.com{funko['imageUrl']}")

        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Funko(bot))