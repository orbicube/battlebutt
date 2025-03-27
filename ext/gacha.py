import discord
from discord.ext import commands
from discord import app_commands

from typing import Optional
import json
import re
from time import time
from datetime import datetime, timedelta
from random import choice, choices, randint, sample

from lxml import html
from credentials import DEBUG_CHANNEL, FNAPI_KEY

class Gacha(commands.Cog,
    command_attrs={"cooldown": commands.CooldownMapping.from_cooldown(
        2, 15, commands.BucketType.user)}):

    headers = {
        "User-Agent": "battlebutt/1.0"
    }

    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command()
    @app_commands.describe(game="Gacha you want to pull a character from")
    async def gacha(self, ctx, game: Optional[str] = None, reason: Optional[str] = None):
        """ Pulls a random character from a gacha game """

        commands = self.get_commands()
        selected_comm = next((
            c for c in commands if c.name == game or game in c.aliases), None)
        if not selected_comm:
            selected_comm = choice(commands)
        await self.bot.get_channel(DEBUG_CHANNEL).send(selected_comm.name)
        await selected_comm.__call__(ctx, reason)


    @gacha.autocomplete('game')
    async def gacha_autocomplete(self, 
        interaction: discord.Interaction,
        current: str,) -> list[app_commands.Choice[str]]:

        games = [c.name for c in self.get_commands() if not c.name == "gacha"]
        completes = [app_commands.Choice(name=game, value=game)
            for game in games if current.lower() in game.lower()]

        if not current:
            completes = sample(completes, len(completes))

        return completes[:25] 


    # @commands.command(aliases=['gbf'])
    # async def granblue(self, ctx):
    #     """ Pulls a random Granblue Fantasy character """

    #     with open("ext/data/gbf.json") as f:
    #         j = json.load(f)
    #     last_up = datetime.utcfromtimestamp(j["updated"])
    #     characters = j["characters"]
    #     if (datetime.utcnow() - last_up) / timedelta(weeks=1) > 1:

    #         params = {
    #             "action": "query",
    #             "list": "cargoquery",
    #             "table": "characters",
    #             "fields": "name,title,art1,art2,art3",
    #             "format": "json",
    #             "limit": 500
    #         }
    #         url = "https://gbf.wiki/api.php"

    #         finished = False
    #         offset = 0
    #         characters = []
    #         while not finished:
    #             params["offset"] = offset
    #             r = await self.bot.http_client.get(url,
    #                 params=params, headers=self.headers)
    #             results = r.json()["cargoquery"]

    #             if len(results) < 500:
    #                 finished = True
    #             else:
    #                 offset += 500

    #             for c in results:
    #                 c = c['title']
    #                 char = {
    #                     "name": f"{c['name'], c['title']}",
    #                     "arts": [c['art1'], c['art2']]
    #                 }
    #                 if c['art3']:
    #                     char['arts'].append(c['art3'])

    #                 characters.append(char)

    #         data = {
    #             "updated": datetime.utcnow().total_seconds(),
    #             "characters": characters
    #         }
    #         with open("ext/data/gbf.json") as f:
    #             json.dump(data, f)

    #     char = choice(characters)
    #     embed = discord.Embed(
    #         title=char['name']
    #     )
    #     embed.set_image(
    #         url=f"https://gbf.wiki/Special:FilePath/{choice(char['arts'])}")
    #     embed.set_footer(text="Granblue Fantasy")


    @commands.command(aliases=['feh'])
    async def fireemblem(self, ctx, reason: Optional[str] = None):
        """ Pulls a random Fire Emblem Heroes character """
        await ctx.defer()

        params = {
            "action": "query",
            "list": "categorymembers",
            "cmtitle": "Category:Heroes",
            "cmlimit": "500",
            "format": "json"
        }
        url = "https://feheroes.fandom.com/api.php"

        finished = False
        article_list = []
        while not finished:
            r = await self.bot.http_client.get(url, 
                params=params, headers=self.headers)
            results = r.json()

            if "continue" in results:
                params["cmcontinue"] = results["continue"]["cmcontinue"]
            else:
                finished = True

            article_list.extend(results["query"]["categorymembers"])

        selected_article = choice(article_list)["title"]
        params = {
            "action": "parse",
            "page": selected_article,
            "format": "json"
        }
        r = await self.bot.http_client.get(url,
            params=params, headers=self.headers)

        page = html.fromstring(r.json()["parse"]["text"]["*"].replace('\"','"'))
        images = page.xpath("//div[@class='fehwiki-tabber']/span/a[1]/@href")

        embed = discord.Embed(title=selected_article)
        embed.set_image(url=choice(images))
        embed.set_footer(text="Fire Emblem Heroes")

        if reason:
            await ctx.send(f"fire emblem {reason}:", embed=embed)
        else:
            await ctx.send(embed=embed)


    @commands.command(aliases=['wotv'])
    async def warofthevisions(self, ctx, reason: Optional[str] = None):
        """ Pulls a random Final Fantasy War of the Visions character """

        url = "https://wotv-calc.com/api/gl/units?forBuilder=1"
        headers = self.headers
        headers["Referer"] = "https://wotv-calc.com/builder/unit"

        r = await self.bot.http_client.get(url, headers=headers)
        character = choice(r.json())

        embed = discord.Embed(title=character["names"]["en"])
        embed.set_image(
            url=f"https://wotv-calc.com/assets/units/{character['image']}.webp")
        embed.set_footer(text="War of the Visions: Final Fantasy Brave Exvius")

        if reason:
            await ctx.send(f"war of the visions {reason}:")
        else:
            await ctx.send(embed=embed)


    @commands.command()
    async def arknights(self, ctx, reason: Optional[str] = None):
        """ Pulls a random Arknights character """

        url = "https://raw.githubusercontent.com/Aceship/AN-EN-Tags/refs/heads/master/json/gamedata/en_US/gamedata/excel/skin_table.json"
        r = await self.bot.http_client.get(url)

        skins = r.json()["charSkins"]
        selected_skin = choice([skin for skin in skins.keys() if "char_" in skin])
        skin_file = skins[selected_skin]['portraitId'].replace('#','%23')

        embed = discord.Embed(
            title=skins[selected_skin]["displaySkin"]["modelName"])
        embed.set_image(url=f"https://raw.githubusercontent.com/Aceship/Arknight-Images/refs/heads/main/characters/{skin_file}.png")
        embed.set_footer(text="Arknights")

        if reason:
            await ctx.send(f"arknights {reason}:", embed=embed)
        else:
            await ctx.send(embed=embed)


    @commands.command()
    async def dragalialost(self, ctx, reason: Optional[str] = None):
        """ Pulls a random Dragalia Lost character """

        url = "https://dragalialost.wiki/api.php"
        params = {
            "action": "parse",
            "page": "Adventurer Grid",
            "format": "json"
        }
        r = await self.bot.http_client.get(url, params=params)
        page = html.fromstring(r.json()["parse"]["text"]["*"].replace('\"','"'))

        images = page.xpath("//img[@data-file-width='1024']")
        character = choice(images)

        char_name = character.xpath("@alt")[0]
        char_img = character.xpath("@src")[0][:-3] + "1000"

        embed = discord.Embed(title=char_name)
        embed.set_image(url=f"https://dragalialost.wiki/{char_img}")
        embed.set_footer(text="Dragalia Lost")

        if reason:
            await ctx.send(f"dragalia lost {reason}:", embed=embed)
        else:
            await ctx.send(embed=embed)


    @commands.command()
    async def mariokarttour(self, ctx, reason: Optional[str] = None):
        """ Pulls a random Mario Kart Tour character """

        await ctx.defer()

        url = "https://www.mariowiki.com/api.php"
        params = {
            "action": "parse",
            "page": "Gallery:Mario_Kart_Tour_sprites_and_models",
            "format": "json"
        }
        r = await self.bot.http_client.get(url, params=params)
        page = html.fromstring(r.json()["parse"]["text"]["*"].replace('\"','"'))

        characters = page.xpath(
            "//span[@id='In-game_portraits']/../following-sibling::ul[1]/li")
        character = choice(characters)

        embed = discord.Embed(title=character.xpath(".//div/p/a/text()")[0])

        img = character.xpath(
            ".//a[@class='image']/@href")[0].split("/File:")[1]
        embed.set_image(url=f"https://www.mariowiki.com/Special:FilePath/{img}")

        embed.set_footer(text="Mario Kart Tour")

        if reason:
            await ctx.send(f"mario kart tour {reason}:", embed=embed)
        else:
            await ctx.send(embed=embed)

    @commands.command()
    async def fortnite(self, ctx, reason: Optional[str] = None):
        """ Posts a random Fortnite skin """
        # Defer in case HTTP requests take too long
        await ctx.defer()

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
            "LavaSeries": "#f39d09",
            "MarvelSeries": "#d70204",
            "PlatformSeries": "#3730FF",
            "ShadowSeries": "#515151",
            "SlurpSeries": "#03f1ed",
            "ColumbusSeries": "#ffaf00"
        }

        # Grab current list of items and pick random one
        url = "https://fortniteapi.io/v2/items/list"
        params = {
            "type": "outfit",
            "fields": "id,name"
        }
        headers = {
            "Authorization": FNAPI_KEY
        }
        r = await self.bot.http_client.get(url, params=params, headers=headers)
        items = r.json()
        skin = choice(items["items"])

        while skin["name"] == "TBD" or not skin["name"] or "_" in skin["name"]:
            skin = choice(items["items"])

        url = "https://fortniteapi.io/v2/items/get"
        params = {
            "id": skin["id"]
        }
        r = await self.bot.http_client.get(url, params=params, headers=headers)
        skin = r.json()["item"]

        # Start crafting embed with data present for all skins
        embed = discord.Embed(
            title=skin["name"],
            description=skin["description"])

        # used to be ass["primaryMode"] == "BattleRoyale", using ass["productTag"] == "Product.BR" temp
        if skin["displayAssets"]:
            br_assets = [ass for ass in skin["displayAssets"] if ass["productTag"] == "Product.BR"]
            embed.set_image(url=choice(br_assets)["background"])
        else:
            embed.set_image(url=skin["images"]["background"])

        # Discord embed colour based on rarity/series
        if skin["series"]:
            embed.colour = discord.Colour(value=0).from_str(
                rarities[skin["series"]["id"]])
        else:
            embed.colour = discord.Colour(value=0).from_str(
                rarities[skin["rarity"]["id"]])

        # If it has a unique set name, put it into the description
        if skin["set"]:
            if skin["set"]["name"] != skin["name"]:
                embed.description += f"\n\n{skin['set']['partOf']}"

        # If Shop skin, display price and time since last appearance
        if skin["price"]:
            footer_text = f"{skin['price']} V-Bucks •"

            days_ago = datetime.utcnow() - datetime.strptime(
                skin["lastAppearance"], "%Y-%m-%d")
            if days_ago.days == 0:
                embed.set_footer(text=f"{footer_text} Currently in the shop")
            else:
                embed.set_footer(text=f"{footer_text} Last seen {days_ago.days} days ago")

        # Format Battle Pass footer
        elif skin["battlepass"]:
            bp_format = re.findall(
                r'Chapter (\d+) - Season (\d+)',
                skin['battlepass']['displayText']['chapterSeason'])[0]
            embed.set_footer(text=f"C{bp_format[0]}S{bp_format[1]} Battle Pass")
            
        # Extra conditionals
        elif not skin["battlepass"]:
            # Battle Pass challenges
            #if "BattlePass.Paid" in skin["gameplayTags"]:
            #    season = re.search(
            #        r'.Season(\d+).BattlePass.Paid', str(skin["gameplayTags"]))
            #    embed.set_footer(text=f"{calc_season_bp(season)} Battle Pass")
            # Crew packs
            if "CrewPack" in skin["gameplayTags"]:
                crewdate = re.findall(
                    r'CrewPack.(\w+)(\d+)', str(skin["gameplayTags"]))[0]
                embed.set_footer(text=f"{crewdate[0]} {crewdate[1]} Crew Pack")

        if reason:
            await ctx.send(f"fortnite {reason}:", embed=embed)
        else:
            await ctx.send(embed=embed)


    # @commands.command(aliases=['fgo'])
    # async def fategrandorder(self, ctx):
    #     """ Pulls a random Fate Grand Order character """

    #     url = "https://fategrandorder.fandom.com/api.php"
    #     params = {
    #         "action": "query",
    #         "list": "categorymembers",
    #         "cmtitle": "Category:Servant",
    #         "cmlimit": "500",
    #         "format": "json"
    #     }
    #     finished = False
    #     article_list = []
    #     while not finished:
    #         r = await self.bot.http_client.get(url, 
    #             params=params, headers=self.headers)
    #         results = r.json()

    #         if "continue" in results:
    #             params["cmcontinue"] = results["continue"]["cmcontinue"]
    #         else:
    #             finished = True

    #         article_list.extend(results["query"]["categorymembers"])

    #     selected_article = choice(article_list)["title"]
    #     params = {
    #         "action": "parse",
    #         "page": selected_article,
    #         "format": "json"
    #     }
    #     r = await self.bot.http_client.get(url,
    #         params=params, headers=self.headers)

        


async def setup(bot):
    await bot.add_cog(Gacha(bot))