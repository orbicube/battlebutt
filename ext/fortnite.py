import discord
from discord.ext import commands
from discord import app_commands

from typing import Optional
import json
import re
from time import time
from datetime import datetime, timedelta
from random import choice

from lxml import html
from credentials import FNAPI_KEY

class Fortnite(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    rarities = {
        "Common": "#B1B1B1",
        "Uncommon": "#5BFD00",
        "Rare": "#00FFF6",
        "Epic": "#D505FF",
        "Legendary": "#F68B20",
        "CUBESeries": "#ff138e",
        "DCUSeries": "#0031e0",
        "FrozenSeries": "#afd7ff",
        "CreatorCollabSeries": "#1be2e4",
        "Series_Lamborghini": "#DDD7ED",
        "Lava_Series": "#f39d09",
        "MarvelSeries": "#d70204",
        "PlatformSeries": "#3730FF",
        "ShadowSeries": "#515151",
        "SlurpSeries": "#03f1ed",
        "ColumbusSeries": "#ffaf00"
    }

    @commands.hybrid_command()
    @app_commands.describe(reason="Why you're pulling a Fortnite")
    async def fortnite(self, ctx, reason: Optional[str]):
        """ Posts a random Fortnite skin """

        # Defer in case HTTP requests take too long
        await ctx.defer()

        # Grab current list of items and pick random one
        url = "https://fortniteapi.io/v2/items/list"
        params = {
            "type": "outfit"
        }
        headers = {
            "Authorization": FNAPI_KEY
        }
        r = await self.bot.http_client.get(url, params=params, headers=headers)
        items = r.json()
        skin = choice(items["items"])

        while skin["name"] == "TBD":
            skin = choice(items["items"])

        # Start crafting embed with data present for all skins
        embed = discord.Embed(
            title=skin["name"],
            description=skin["description"])

        embed.set_image(url=skin["images"]["background"])

        # Discord embed colour based on rarity/series
        if skin["series"]:
            embed.colour = discord.Colour(value=0).from_str(
                self.rarities[skin["series"]["id"]])
        else:
            embed.colour = discord.Colour(value=0).from_str(
                self.rarities[skin["rarity"]["id"]])

        # If it has a unique set name, put it into the description
        if skin["set"]:
            if skin["set"]["name"] != skin["name"]:
                embed.description += f"\n\n{skin['set']['partOf']}"

        # If Shop skin, display price and time since last appearance
        if skin["price"]:
            days_ago = datetime.utcnow() - datetime.strptime(
                skin["lastAppearance"], "%Y-%m-%d")
            embed.set_footer(text=f"{skin['price']} V-Bucks • Last seen {days_ago.days} days ago")
        # Format Battle Pass footer
        elif skin["battlepass"]:
            bp_format = re.findall(
                r'Chapter (\d+) - Season (\d+)',
                skin['battlepass']['displayText']['chapterSeason'])[0]
            embed.set_footer(text=f"C{bp_format[0]}S{bp_format[1]} Battle Pass")
        # Extra conditionals
        elif not skin["battlepass"]:
            # Battle Pass challenges
            if "BattlePass.Paid" in skin["gameplayTags"]:
                season = re.search(
                    r'.Season(\d+).BattlePass.Paid', str(skin["gameplayTags"]))
                embed.set_footer(text=f"{calc_season_bp(season)} Battle Pass")
            # Crew packs
            elif "CrewPack" in skin["gameplayTags"]:
                crewdate = re.findall(
                    r'CrewPack.(\w+)(\d+)', str(skin["gameplayTags"]))[0]
                embed.set_footer(text=f"{crewdate[0]} {crewdate[1]} Crew Pack")

        await ctx.send(embed=embed)


    def calc_season_bp(season: int):
        if season > 27:
            return f"C5S{season % 27}"
        elif season > 22:
            return f"C4S{season % 22}"
        elif season > 18:
            return f"C3S{season % 18}"
        elif season > 10:
            return f"C3S{season % 10}"


async def setup(bot):
    await bot.add_cog(Fortnite(bot))