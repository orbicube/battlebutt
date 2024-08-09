import discord
from discord.ext import commands
from discord import app_commands

from random import randint, choice, choices
from datetime import datetime
from io import BytesIO
from typing import Optional

class Funko(commands.Cog,
    command_attrs={"cooldown": commands.CooldownMapping.from_cooldown(
        1, 30, commands.BucketType.user)}):

    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command()
    @app_commands.describe(reason="Why you're pulling a Funko")
    async def funko(self, ctx, reason: Optional[str]):
        """ Posts a random Funko Pop figure """

        # Defer in case HTTP requests take too long
        await ctx.defer()

        url = "https://mobilesearch-prod.funko.com/product_search"
        headers = {
            "User-Agent": "Popspedia/15 CFNetwork/1490.0.4 Darwin/23.2.0"
        }

        # API cannot paginate beyond 10k results so we need to filter.
        # Search results contain metadata on matching items, which we can use
        # to pick a random license with proper weighting to filter results.

        params = {
            "refine_4": "c_productType=Pop!",
            "count": 1
        }

        r = await self.bot.http_client.get(url, headers=headers, params=params)
        results = r.json()

        # Randomly pick a year based on weighting from item counts.
        licenses = [license['value'] for license in results['refinements'][4]['values']]
        counts = [license['hit_count'] for license in results['refinements'][4]['values']]
        license = choices(licenses, counts)[0]

        # Get that year's associated count.
        license_count = counts[licenses.index(license)]

        # 10 items per page so divide item count by 10 and round up.
        params['start'] = randint(0, license_count-1)
        params['refine_5'] = f"c_license={license}"

        r = await self.bot.http_client.get(url, headers=headers, params=params)
        results = r.json()

        funko = results['hits'][0]
        embed = discord.Embed(
            title = funko['c_mobileDisplayName'],
            color = 0xCCAB4B)

        # Convert timestamp to human-readable string ("Year"/"Month Xth, Year")
        release_date = datetime.strptime(
            funko['c_releaseDate'].split('T')[0],
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

        try:
            embed.add_field(
                name = "Value",
                value = f"${funko['c_sortValue']:n}",
                inline = True)
        except:
            pass

        embed.set_footer(text=funko['c_license'])

        embed.set_image(url=funko['image']['link'])

        if reason and ctx.interaction:
            await ctx.send(f"funko {reason}:", embed=embed)
        else:
            await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Funko(bot))