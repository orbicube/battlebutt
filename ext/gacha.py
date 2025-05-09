import discord
from discord.ext import commands
from discord import app_commands

from typing import Optional
import json
import csv
import re
from time import time
from datetime import datetime, timedelta
from random import choice, choices, randint, sample

from urllib.parse import quote
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
        """ Pulls a character from a gacha game """

        commands = self.get_commands()
        selected_comm = next((
            c for c in commands if c.name == game or game in c.aliases), None)
        if not selected_comm:
            selected_comm = choice(commands)
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


    @commands.command(aliases=['gbf'])
    async def granblue(self, ctx, reason: Optional[str] = None):
        """ Pulls a Granblue Fantasy character """

        with open("ext/data/gbf.json") as f:
            j = json.load(f)
        last_up = datetime.utcfromtimestamp(j["updated"])
        characters = j["characters"]
        if (datetime.utcnow() - last_up) / timedelta(weeks=1) > 1:

            params = {
                "action": "cargoquery",
                "tables": "characters",
                "fields": "name,title,art1,art2,art3",
                "format": "json",
                "limit": 500
            }
            url = "https://gbf.wiki/api.php"

            finished = False
            offset = 0
            characters = []
            while not finished:
                params["offset"] = offset
                r = await self.bot.http_client.get(url,
                    params=params, headers=self.headers)
                results = r.json()["cargoquery"]

                if len(results) < 500:
                    finished = True
                else:
                    offset += 500

                for c in results:
                    c = c['title']
                    char = {
                        "name": f"{c['name']}, {c['title']}".replace('&#039;','\''),
                        "arts": [quote(c['art1']), quote(c['art2'])]
                    }
                    if c['art3']:
                        char['arts'].append(quote(c['art3']))

                    # Edge case with encoding of mu character 
                    if '\u03bc' in char['name']:
                        char['name'] = char['name'].split(',')[0]
                        arts = []
                        for art in char['arts']:
                            new_art = f"%CE%BC%27s%20{art.split('%20')[1]}"
                            arts.append(new_art)
                        char['arts'] = arts

                    characters.append(char)

            data = {
                "updated": int(datetime.utcnow().timestamp()),
                "characters": characters
            }
            with open("ext/data/gbf.json", "w") as f:
                json.dump(data, f)

        char = choice(characters)
        embed = discord.Embed(
            title=char['name'],
            color=0x1ca6ff
        )
        embed.set_image(
            url=f"https://gbf.wiki/Special:FilePath/{choice(char['arts'])}")
        embed.set_footer(text="Granblue Fantasy")

        if reason and ctx.interaction:
            await ctx.send(f"granblue {reason}:", embed=embed)
        else:
            await ctx.send(embed=embed)


    @commands.command(aliases=['feh'])
    async def fireemblem(self, ctx, reason: Optional[str] = None):
        """ Pulls a Fire Emblem Heroes character """
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
            params=params, headers=self.headers, timeout=15)

        page = html.fromstring(r.json()["parse"]["text"]["*"].replace('\"','"'))
        images = page.xpath("//div[@class='fehwiki-tabber']/span/a[1]/@href")

        embed = discord.Embed(
            title=selected_article,
            color=0xc3561f)
        try:
            embed.set_image(url=choice(images))
        except:
            await self.bot.get_channel(DEBUG_CHANNEL).send(f"feh: {selected_article}")
        embed.set_footer(text="Fire Emblem Heroes")

        if reason and ctx.interaction:
            await ctx.send(f"fire emblem {reason}:", embed=embed)
        else:
            await ctx.send(embed=embed)


    @commands.command(aliases=['wotv'])
    async def warofthevisions(self, ctx, reason: Optional[str] = None):
        """ Pulls a Final Fantasy War of the Visions character """

        url = "https://wotv-calc.com/api/gl/units?forBuilder=1"
        headers = self.headers
        headers["Referer"] = "https://wotv-calc.com/builder/unit"

        r = await self.bot.http_client.get(url, headers=headers)
        character = choice(r.json())

        embed = discord.Embed(
            title=character["names"]["en"],
            color=0x2c4584)
        embed.set_image(
            url=f"https://wotv-calc.com/assets/units/{character['image']}.webp")
        embed.set_footer(text="War of the Visions: Final Fantasy Brave Exvius")

        if reason and ctx.interaction:
            await ctx.send(f"war of the visions {reason}:")
        else:
            await ctx.send(embed=embed)


    @commands.command()
    async def arknights(self, ctx, reason: Optional[str] = None):
        """ Pulls an Arknights character """

        url = "https://raw.githubusercontent.com/Aceship/AN-EN-Tags/refs/heads/master/json/gamedata/en_US/gamedata/excel/skin_table.json"
        r = await self.bot.http_client.get(url)

        skins = r.json()["charSkins"]
        selected_skin = choice([skin for skin in skins.keys() if "char_" in skin])
        skin_file = skins[selected_skin]['portraitId'].replace('#','%23')

        embed = discord.Embed(
            title=skins[selected_skin]["displaySkin"]["modelName"],
            color=0xfcda16)
        embed.set_image(url=f"https://raw.githubusercontent.com/Aceship/Arknight-Images/refs/heads/main/characters/{skin_file}.png")
        embed.set_footer(text="Arknights")

        if reason and ctx.interaction:
            await ctx.send(f"arknights {reason}:", embed=embed)
        else:
            await ctx.send(embed=embed)


    @commands.command()
    async def dragalialost(self, ctx, reason: Optional[str] = None):
        """ Pulls a Dragalia Lost character """

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

        embed = discord.Embed(
            title=char_name,
            colour=0x3e91f1)
        embed.set_image(url=f"https://dragalialost.wiki/{char_img}")
        embed.set_footer(text="Dragalia Lost")

        if reason and ctx.interaction:
            await ctx.send(f"dragalia lost {reason}:", embed=embed)
        else:
            await ctx.send(embed=embed)


    @commands.command(aliases=['mkt'])
    async def mariokarttour(self, ctx, reason: Optional[str] = None):
        """ Pulls a Mario Kart Tour character """

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
        characters += page.xpath(
            "//span[@id='Mii_Racing_Suits']/../following-sibling::ul[1]/li")
        character = choice(characters)

        # No link if character is Mii
        name = character.xpath(".//div/p/text()")[0]
        if len(name) < 2:
            name = character.xpath(".//div/p/a/text()")[0]

        embed = discord.Embed(
            title=name,
            color=0xe60012)

        img = character.xpath(
            ".//a[@class='image']/@href")[0].split("/File:")[1]
        embed.set_image(url=f"https://www.mariowiki.com/Special:FilePath/{img}")

        embed.set_footer(text="Mario Kart Tour")

        if reason and ctx.interaction:
            await ctx.send(f"mario kart tour {reason}:", embed=embed)
        else:
            await ctx.send(embed=embed)


    @commands.command()
    async def fortnite(self, ctx, reason: Optional[str] = None):
        """ Posts a Fortnite skin """
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

        if reason and ctx.interaction:
            await ctx.send(f"fortnite {reason}:", embed=embed)
        else:
            await ctx.send(embed=embed)


    @commands.command(aliases=['fgo'])
    async def fategrandorder(self, ctx, reason: Optional[str] = None):
        """ Pulls a Fate Grand Order character """

        url = "https://fategrandorder.fandom.com/api.php"
        params = {
            "action": "query",
            "list": "categorymembers",
            "cmtitle": "Category:Servant",
            "cmlimit": "500",
            "format": "json"
        }
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

        images = page.xpath("//div[@class='pi-image-collection wds-tabber']/div[@class='wds-tab__content']/figure/a/@href")
        
        embed = discord.Embed(
            title=selected_article,
            color=0xece9d6)
        embed.set_image(url=choice([i for i in images if 'Sprite' not in i]))
        embed.set_footer(text="Fate/Grand Order")

        if reason and ctx.interaction:
            await ctx.send(f"fate/grand order {reason}:", embed=embed)
        else:
            await ctx.send(embed=embed)


    @commands.command(aliases=['nier'])
    async def nierreincarnation(self, ctx, reason: Optional[str] = None):
        """ Pulls a NieR Re[in]carnation character """

        with open("ext/data/nier.json") as f:
            char = choice(json.load(f))

        embed = discord.Embed(
            title=char["name"],
            colour=0x3b70c7)
        embed.set_image(
            url=f"https://assets.nierrein.guide/ui/costume/{char['id']}/{char['id']}_full.png")
        embed.set_footer(text="NieR Re[in]carnation")

        if reason and ctx.interaction:
            await ctx.send(f"nier reincarnation {reason}:", embed=embed)
        else:
            await ctx.send(embed=embed)


    @commands.command(aliases=['r1999'])
    async def reverse1999(self, ctx, reason: Optional[str] = None):
        """ Pulls a Reverse 1999 character """

        url = "https://www.prydwen.gg/page-data/re1999/characters/"

        r = await self.bot.http_client.get(f"{url}page-data.json")
        char = choice(
            r.json()["result"]["data"]["allCharacters"]["nodes"])["slug"]

        r = await self.bot.http_client.get(f"{url}{char}/page-data.json")
        c_data = r.json()["result"]["data"]["currentUnit"]["nodes"][0]

        skins = [(c_data["name"], c_data["imageFull"]["localFile"]["childImageSharp"]["gatsbyImageData"]["images"]["fallback"]["src"])]

        if c_data["imageInsight"]:
            skins.append((c_data["name"], c_data["imageInsight"]["localFile"]["childImageSharp"]["gatsbyImageData"]["images"]["fallback"]["src"]))

        #if c_data["skins"]:
        #    for sk in c_data["skins"]:
        #        skins.append((f"{c_data['name']}, {sk['name']}", sk["imageFull"]["localFile"]["childImageSharp"]["gatsbyImageData"]["images"]["fallback"]["src"]))

        skin = choice(skins)
        embed = discord.Embed(
            title=skin[0],
            color=0x53443c)
        embed.set_image(url=f"https://www.prydwen.gg{skin[1]}")
        embed.set_footer(text="Reverse 1999")

        if reason and ctx.interaction:
            await ctx.send(f"reverse 1999 {reason}:", embed=embed)
        else:
            await ctx.send(embed=embed)


    @commands.command(aliases=['atelier'])
    async def atelieresleriana(self, ctx, reason: Optional[str] = None):
        """ Pulls an Atelier Resleriana character """

        # JSON Updated March 29, 2025
        with open("ext/data/atelier.json") as f:
            char = choice(json.load(f))

        embed = discord.Embed(
            title=char["name"],
            color=0x845b51)
        embed.set_image(
            url=f"https://barrelwisdom.com/media/games/resleri/characters/full/{char['slug']}.webp")
        embed.set_footer(
            text="Atelier Reseleriana")

        if reason and ctx.interaction:
            await ctx.send(f"atelier {reason}:", embed=embed)
        else:
            await ctx.send(embed=embed)


    @commands.command()
    async def sinoalice(self, ctx, reason: Optional[str] = None):
        """ Pulls a SINoALICE character """

        chars = []
        with open("ext/data/sinoalice.csv", newline='', encoding='utf-8') as f:
            reader = csv.reader(f, delimiter=';')
            for row in reader:
                chars.append(row)

        char = choice(chars)

        embed = discord.Embed(
            title=f"{char[1]}/{char[2]}",
            color=0xfafafa)
        embed.set_image(url=f"https://sinoalice.game-db.tw/images/character_l/{char[0]}.png")
        embed.set_footer(text="SINoALICE")

        if reason and ctx.interaction:
            await ctx.send(f"sinoalice {reason}:", embed=embed)
        else:
            await ctx.send(embed=embed)


    @commands.command(aliases=['touhou'])
    async def touhoulostword(self, ctx, reason: Optional[str] = None):
        """ Pulls a Touhou LostWord character """

        with open("ext/data/touhou.json") as f:
            j = json.load(f)
        last_up = datetime.utcfromtimestamp(j["updated"])
        characters = j["characters"]
        if (datetime.utcnow() - last_up) / timedelta(weeks=2) > 1:
            r = await self.bot.http_client.get(
                "https://lostwordchronicle.com/characters/ajax")
            results = r.json()["data"]

            characters = []
            for r in results:
                char = {
                    "name": f"{r['name']} ({r['universe']})",
                    "id": r['character']
                }
                characters.append(char)

            data = {
                "updated": int(datetime.utcnow().timestamp()),
                "characters": characters
            }
            with open("ext/data/touhou.json", "w") as f:
                json.dump(data, f)


        char = choice(characters)

        r = await self.bot.http_client.get(
            f"https://lostwordchronicle.com/lorepedia/characters/{char['id']}")
        page = html.fromstring(r.text)

        costumes = page.xpath("//div[@id='character-costume']/div/img/@src")
        picked_costume = randint(0, len(costumes)-1)

        costume_title = page.xpath(
            f"//div[@id='costume-information']/p[@id='costume-title-{picked_costume}']/text()")[0]

        embed = discord.Embed(
            title=char["name"],
            description=costume_title,
            color=0xef5a68)
        embed.set_image(
            url=f"https://lostwordchronicle.com{costumes[picked_costume]}")
        embed.set_footer(
            text="Touhou LostWord")

        if reason and ctx.interaction:
            await ctx.send(f"touhou {reason}:", embed=embed)
        else:
            await ctx.send(embed=embed)


    @commands.command()
    async def worldflipper(self, ctx, reason: Optional[str] = None):

        with open("ext/data/worldflipper.json", encoding="utf-8") as f:
            characters = json.load(f)

        url = "https://eliya-bot.herokuapp.com/img/assets/chars/"

        char = choice(characters)
        embed = discord.Embed(
            title=char["name"],
            description=char["title"],
            color=0xb2d8ee)

        embed.set_image(
            url=f"{url}{char['id']}/full_shot_{randint(0,1)}.png")
        embed.set_footer(
            text= "World Flipper")

        if reason and ctx.interaction:
            await ctx.send(f"world flipper {reasonm}:", embed=embed)
        else:
            await ctx.send(embed=embed)




async def setup(bot):
    await bot.add_cog(Gacha(bot))