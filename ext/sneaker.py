import discord
from discord.ext import commands
from discord import app_commands

from random import randint, choice, choices
from datetime import datetime
from typing import Optional

from credentials import SNEAK_KEY

class Sneaker(commands.Cog,
    command_attrs={"cooldown": commands.CooldownMapping.from_cooldown(
        1, 30, commands.BucketType.user)}):

    def __init__(self, bot):
        self.bot = bot

    colours = {
        "white": 0xededed,
        "grey": 0x919291,
        "black": 0x000000,
        "green": 0x6fdd24,
        "teal": 0x6edcde,
        "blue": 0x0126ff,
        "purple": 0x9249de,
        "pink": 0xf091e8,
        "red": 0xfd0209,
        "orange": 0xf96d00,
        "yellow": 0xfce906,
        "cream": 0xfbf4dc,
        "tan": 0xd0bba2,
        "brown": 0x8c663d,
        "silver": 0x999b9b,
        "gold": 0xb49b57,
        "copper": 0xc47e5a,
    }

    @commands.hybrid_command()
    @app_commands.describe(reason="Why you're pulling a sneaker")
    async def sneaker(self, ctx, reason: Optional[str]):
        """ Posts a random sneaker """

        await ctx.defer()

        url = "https://goat.cnstrc.com/browse/group_id/sneakers"
        headers = {
            "User-Agent": "GOAT/2229 CFNetwork/1568.200.51 Darwin/24.1.0"
        }
        params = {
            "key": SNEAK_KEY,
            "page": 1
        }

        # Randomly pick a brand weighting from their item counts
        r = await self.bot.http_client.get(url, headers=headers, params=params)
        results = r.json()["response"]["facets"]

        brand_list = next(
            (i for i in results if i["name"] == "brand"), None)["options"]
        brands = [brand["value"] for brand in brand_list]
        brand_names = [brand["display_name"] for brand in brand_list]
        brand_counts = [brand["count"] for brand in brand_list]

        # Loop til we find a shoe with an image
        shoe_found = False
        while not shoe_found:
            brand = choices(brands, brand_counts)[0]
            brand_name = brand_names[brands.index(brand)]
            params["filters[brand]"] = brand

            # Get counts of brand's yearly releases as limited to 10k results
            r = await self.bot.http_client.get(
                url, headers=headers, params=params)
            results = r.json()["response"]["facets"]

            year_list = next(
                (i for i in results if i["name"] == "release_date_year"),
                None)["options"]
            years = [year["value"] for year in year_list]
            year_counts = [year["count"] for year in year_list]

            year = choices(years, year_counts)[0]
            year_count = year_counts[years.index(year)]

            params["filters[release_date_year]"] = year
            params["page"] = randint(1, int(year_count/20)+1)

            r = await self.bot.http_client.get(
                url, headers=headers, params=params)
            results = r.json()["response"]["results"]

            shoe = choice(results)
            if "image_url" in shoe["data"]:
                shoe_found = True

                if shoe["value"].startswith(brand_name):
                    shoe_name = shoe["value"].split(f"{brand_name} ")[1]
                else:
                    shoe_name = shoe["value"]

                try:
                    colour = self.colours[shoe["data"]["color"]]
                except:
                    colour = discord.Color.from_frb(
                        randint(0,255), randint(0,255), randint(0,255))

                embed = discord.Embed(
                    title=shoe_name,
                    color=colour)

                embed.set_author(name=brand_name)
                embed.set_image(url=shoe["data"]["image_url"])

                release_date = datetime.strptime(
                    shoe["data"]["release_date_time"],
                    "%Y-%m-%d %H:%M:%S")
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

                shoe_price = ""
                if "lowest_price_cents" in shoe["data"]:
                    shoe_price = int(shoe["data"]["lowest_price_cents"] / 100)
                elif "retail_price_cents" in shoe["data"]:
                    shoe_price = int(shoe["data"]["retail_price_cents"] / 100)
                if shoe_price:
                    embed.add_field(
                        name = "Value",
                        value = f"${shoe_price}",
                        inline = True)
                
                if reason and ctx.interaction:
                    await ctx.send(f"sneaker {reason}:", embed=embed)
                else:
                    await ctx.send(embed=embed)              

async def setup(bot):
    await bot.add_cog(Sneaker(bot))








