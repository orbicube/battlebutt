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
from base64 import b64decode
from io import BytesIO
from PIL import Image
from urllib.parse import quote
from lxml import html
from zipfile import ZipFile
import os

from credentials import DEBUG_CHANNEL, FNAPI_KEY, GITHUB_KEY, ERROR_CHANNEL

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
        if ctx.interaction:
            ctx.interaction.extras = {"rando": False}
        if not selected_comm:
            selected_comm = choice(commands)
            await self.bot.get_channel(DEBUG_CHANNEL).send(f"{selected_comm.name}")
            if ctx.interaction:
                ctx.interaction.extras["rando"] = True
        await selected_comm.__call__(ctx, reason)


    @gacha.autocomplete('game')
    async def gacha_autocomplete(self, interaction: discord.Interaction,
        current: str,) -> list[app_commands.Choice[str]]:

        games = [c.name for c in self.get_commands() if not c.name == "gacha"]
        completes = [app_commands.Choice(name=game, value=game)
            for game in games if current.lower() in game.lower()]

        if not current:
            completes = sample(completes, len(completes))

        return completes[:25] 


    @commands.command(aliases=['gbf'], hidden=True)
    async def granblue(self, ctx, reason: Optional[str] = None):
        await ctx.defer()

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
                        "name": c['name'].replace('&#039;','\''),
                        "title": c['title'].replace('&#039;','\''),
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
        img = choice(char['arts'])

        r = await self.bot.http_client.get(
            f"https://gbf.wiki/Special:FilePath/{img}",
            follow_redirects=True)
        char_img = Image.open(BytesIO(r.content))
        char_img = char_img.crop(char_img.getbbox())

        img_path = str(r.url).rsplit('/', 1)[1]

        with BytesIO() as img_binary:
            char_img.save(img_binary, 'PNG')
            img_binary.seek(0)
            file = discord.File(fp=img_binary, filename=f"{img_path}")

        embed = discord.Embed(
            title=char['name'],
            description=char['title'],
            color=0x1ca6ff
        )
        embed.set_image(
            url=f"attachment://{img_path}")
        embed.set_footer(text="Granblue Fantasy")

        if reason and ctx.interaction:
            await ctx.send(f"{'gacha' if ctx.interaction.extras['rando'] else 'granblue'} {reason}:", embed=embed, file=file)
        else:
            await ctx.send(embed=embed, file=file)


    @commands.command(aliases=['feh'])
    async def fireemblem(self, ctx, reason: Optional[str] = None):    
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

            for article in results["query"]["categorymembers"]:
                if article["ns"] == 0:
                    article_list.append(article["title"])

        selected_article = choice(article_list)
        await self.bot.get_channel(DEBUG_CHANNEL).send(f"feh {selected_article}")
        params = {
            "action": "parse",
            "page": selected_article,
            "format": "json"
        }
        r = await self.bot.http_client.get(url,
            params=params, headers=self.headers, timeout=15)

        page = html.fromstring(r.json()["parse"]["text"]["*"].replace('\"','"'))
        img = choice(page.xpath("//div[@class='fehwiki-tabber']/span/a[1]/img/@data-image-key"))

        r = await self.bot.http_client.get(
            f"https://feheroes.fandom.com/wiki/Special:FilePath/{img}",
            follow_redirects=True)
        char_img = Image.open(BytesIO(r.content))
        char_img = char_img.crop(char_img.getbbox())

        with BytesIO() as img_binary:
            char_img.save(img_binary, 'WEBP')
            img_binary.seek(0)
            file = discord.File(fp=img_binary, filename=img)

        embed = discord.Embed(
            title=selected_article.split(":")[0],
            description=selected_article.split(": ")[1],
            color=0xc3561f)
        embed.set_image(url=f"attachment://{img}")
        embed.set_footer(text="Fire Emblem Heroes")

        if reason and ctx.interaction:
            await ctx.send(f"{'gacha' if ctx.interaction.extras['rando'] else 'fire emblem'} {reason}:", embed=embed, file=file)
        else:
            await ctx.send(embed=embed, file=file)


    @commands.command(aliases=['wotv'])
    async def warofthevisions(self, ctx, reason: Optional[str] = None):

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
            await ctx.send(f"{'gacha' if ctx.interaction.extras['rando'] else 'war of the visions'} {reason}:", embed=embed)
        else:
            await ctx.send(embed=embed)


    @commands.command()
    async def arknights(self, ctx, reason: Optional[str] = None):

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
            await ctx.send(f"{'gacha' if ctx.interaction.extras['rando'] else 'arknights'} {reason}:", embed=embed)
        else:
            await ctx.send(embed=embed)


    @commands.command()
    async def dragalialost(self, ctx, reason: Optional[str] = None):
        await ctx.defer()

        url = ("https://api.github.com/repos/orbicube/draglost/git/trees/"
            "fd97dddadcc4347e5b98dd9e747f6a6bc9b430cd")
        headers = { "Authorization": f"Bearer {GITHUB_KEY}" }
        r = await self.bot.http_client.get(url, headers=headers)
        char = choice(r.json()["tree"])

        name, title = char["path"][:-4].split("#")

        r = await self.bot.http_client.get(char["url"], headers=headers)
        img = b64decode(r.json()["content"])
        file = discord.File(fp=BytesIO(img), filename="dragalialost.png")

        embed = discord.Embed(
            title=name,
            description=title,
            colour=0x3e91f1)
        embed.set_image(url="attachment://dragalialost.png")
        embed.set_footer(text="Dragalia Lost")

        if reason and ctx.interaction:
            await ctx.send(f"{'gacha' if ctx.interaction.extras['rando'] else 'dragalia lost'} {reason}:", embed=embed, file=file)
        else:
            await ctx.send(embed=embed, file=file)


    @commands.command(aliases=['mkt'])
    async def mariokarttour(self, ctx, reason: Optional[str] = None):
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

        name = character.xpath(".//div/p/a/text()")[0]
        title = ""
        if " (" in name:
            name, title = name.rsplit(" (", 1)
            title = title[:-1] 

        embed = discord.Embed(
            title=name,
            description=title,
            color=0xe60012)

        img = character.xpath(".//a[@class='image']/img/@src")[0].rsplit("/", 1)[0].replace('/thumb', '')
        embed.set_image(url=img)

        embed.set_footer(text="Mario Kart Tour")

        if reason and ctx.interaction:
            await ctx.send(f"{'gacha' if ctx.interaction.extras['rando'] else 'mario kart tour'} {reason}:", embed=embed)
        else:
            await ctx.send(embed=embed)


    @commands.command()
    async def fortnite(self, ctx, reason: Optional[str] = None):
        await ctx.defer()

        url = "https://fortnite.fandom.com/api.php"

        with open("ext/data/fortnite.json", encoding="utf-8") as f:
            j = json.load(f)
        last_up = datetime.utcfromtimestamp(j["updated"])
        characters = j["characters"]
        if (datetime.utcnow() - last_up) / timedelta(weeks=1) > 1:
            params = {
                "action": "query",
                "list": "categorymembers",
                "cmtitle": "Category:Outfits",
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

                for article in results["query"]["categorymembers"]:
                    if article["pageid"] not in j["bad_pages"] and article["ns"] == 0:
                        article_list.append(
                            {"pageid": article["pageid"],
                            "title": article["title"]})

            j["characters"] = article_list
            j["updated"] = int(datetime.utcnow().timestamp())
            with open("ext/data/fortnite.json", "w") as f:
                json.dump(j, f)

        char = choice(characters)

        params = {
            "action": "parse",
            "page": char["title"],
            "format": "json"
        }
        r = await self.bot.http_client.get(url,
            params=params, headers=self.headers)
        page = html.fromstring(r.json()["parse"]["text"]["*"].replace('\"','"'))
        images = page.xpath("//aside//img[@class='pi-image-thumbnail']")

        featured = []
        for image in images:
            img_url = image.xpath("./@data-image-key")[0]
            if "Featured)" in img_url:
                featured.append(img_url)

        if not featured:
            await self.bot.get_channel(ERROR_CHANNEL).send(
                f"No featured image found, potentially bad page: {char['title']} (ID: {char['pageid']})")
            await testnite(ctx, reason)

        img = choice(featured)

        r = await self.bot.http_client.get(
            f"https://fortnite.fandom.com/wiki/Special:FilePath/{img}",
            follow_redirects=True)
        char_img = Image.open(BytesIO(r.content))
        char_img = char_img.crop(char_img.getbbox())

        with BytesIO() as img_binary:
            char_img.save(img_binary, 'PNG')
            img_binary.seek(0)
            file = discord.File(fp=img_binary, filename=img)

        if " (Outfit)" in char["title"]:
            char["title"] = char["title"][:-9]

        embed = discord.Embed(
            title=char["title"],
            color=0xad2fea)
        embed.set_image(url=f"attachment://{img}")
        embed.set_footer(text="Fortnite")

        if reason and ctx.interaction:
            await ctx.send(f"{'gacha' if ctx.interaction.extras['rando'] else 'fortnite'} {reason}:", embed=embed, file=file)
        else:
            await ctx.send(embed=embed, file=file)


    @commands.command(aliases=['fgo'])
    async def fategrandorder(self, ctx, reason: Optional[str] = None):
        await ctx.defer()

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

            bad_pages = [24917, 64670, 383442, 111081, 579165, 623674, 603920,
                602461, 658001, 123993, 34471, 34468, 631866, 6665513, 78799,
                509030, 663419, 635637, 671627, 635810, 640684, 565396, 602786,
                410778, 124402, 253574, 666612, 603989, 670436, 547889, 410804,
                78805, 8077, 674121, 292832, 576046, 26980, 74218, 633911, 
                585580, 650647, 34469, 644422, 34470]
            for article in results["query"]["categorymembers"]:
                if article["pageid"] not in bad_pages:
                    article_list.append(article)

        selected_article = choice(article_list)["title"]
        await self.bot.get_channel(DEBUG_CHANNEL).send(f"fgo {selected_article}")
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
            await ctx.send(f"{'gacha' if ctx.interaction.extras['rando'] else 'fate/grand order'} {reason}:", embed=embed)
        else:
            await ctx.send(embed=embed)


    @commands.command(aliases=['nier'])
    async def nierreincarnation(self, ctx, reason: Optional[str] = None):
        await ctx.defer()

        url = ("https://api.github.com/repos/orbicube/nierrein/git/trees/"
            "a5010db7dc892bf89feda0bb305e3f9bc5538858")
        headers = { "Authorization": f"Bearer {GITHUB_KEY}" }
        r = await self.bot.http_client.get(url, headers=headers)
        char = choice(r.json()["tree"])

        name, title = char["path"][:-4].split("#")

        r = await self.bot.http_client.get(char["url"], headers=headers)
        img = b64decode(r.json()["content"])
        file = discord.File(fp=BytesIO(img), filename="nierreincarnation.png")

        embed = discord.Embed(
            title=name,
            description=title,
            colour=0x3b70c7)
        embed.set_image(url="attachment://nierreincarnation.png")
        embed.set_footer(text="NieR Re[in]carnation")

        if reason and ctx.interaction:
            await ctx.send(f"{'gacha' if ctx.interaction.extras['rando'] else 'nier reincarnation'} {reason}:", embed=embed, file=file)
        else:
            await ctx.send(embed=embed, file=file)


    @commands.command(aliases=['r1999'])
    async def reverse1999(self, ctx, reason: Optional[str] = None):
        await ctx.defer()

        params = {
            "action": "query",
            "list": "categorymembers",
            "cmtitle": "Category:Garments",
            "cmlimit": "500",
            "format": "json"
        }
        url = "https://reverse1999.fandom.com/api.php"

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

            for c in results["query"]["categorymembers"]:
                if c["ns"] == 0:
                    article_list.append(c["title"])

        valid_article = False
        while not valid_article:
            selected_article = choice(article_list)
            params = {
                "action": "parse",
                "page": selected_article,
                "format": "json"
            }
            r = await self.bot.http_client.get(url,
                params=params, headers=self.headers, timeout=15)

            page = html.fromstring(
                r.json()["parse"]["text"]["*"].replace('\"','"'))
            
            try:
                unreleased_test = page.xpath(
                    "//div[@class='wds-tabs__tab-label']/a/text()")[1]
                if "TBA" not in unreleased_test:
                    valid_article = True
            except:
                valid_article = True

        skin = choice(page.xpath("//div[@class='psychube']"))

        name = skin.xpath(".//div/div/div[2]/text()")[0]
        title = skin.xpath(".//div/div/p/text()")[0][2:]
        img = skin.xpath(".//figure/a/img/@data-image-key")[0]
        await self.bot.get_channel(DEBUG_CHANNEL).send(f"r1999 {img}")

        r = await self.bot.http_client.get(
            f"https://reverse1999.fandom.com/wiki/Special:FilePath/{img}",
            follow_redirects=True)
        char_img = Image.open(BytesIO(r.content))
        char_img = char_img.crop(char_img.getbbox())

        with BytesIO() as img_binary:
            char_img.save(img_binary, 'PNG')
            img_binary.seek(0)
            file = discord.File(fp=img_binary, filename=img)

        embed = discord.Embed(
            title=name,
            color=0x53443c)
        if "Default" not in title:
            embed.description = title
        embed.set_image(url=f"attachment://{img}")
        embed.set_footer(text="Reverse: 1999")

        if reason and ctx.interaction:
            await ctx.send(f"{'gacha' if ctx.interaction.extras['rando'] else 'reverse1999'} {reason}:", embed=embed, file=file)
        else:
            await ctx.send(embed=embed, file=file)


    #@commands.command(aliases=['atelier'])
    async def atelieresleriana(self, ctx, reason: Optional[str] = None):
        await ctx.defer()

        # JSON Updated March 29, 2025
        with open("ext/data/atelier.json") as f:
            char = choice(json.load(f))

        embed = discord.Embed(
            title=char["name"],
            description=char["title"],
            color=0x845b51)
        embed.set_image(
            url=f"https://barrelwisdom.com/media/games/resleri/characters/full/{char['slug']}.webp")
        embed.set_footer(
            text="Atelier Reseleriana")

        if reason and ctx.interaction:
            await ctx.send(f"{'gacha' if ctx.interaction.extras['rando'] else 'atelier'} {reason}:", embed=embed)
        else:
            await ctx.send(embed=embed)


    @commands.command()
    async def sinoalice(self, ctx, reason: Optional[str] = None):
        await ctx.defer()

        url = ("https://api.github.com/repos/orbicube/sinoalice/git/trees/"
            "1b0c543065d69fa45d4cebcd539ff900e2517020")
        headers = { "Authorization": f"Bearer {GITHUB_KEY}" }
        r = await self.bot.http_client.get(url, headers=headers)
        char = choice(r.json()["tree"])

        name, title = char["path"][:-4].split("#")

        r = await self.bot.http_client.get(char["url"], headers=headers)
        img = b64decode(r.json()["content"])
        file = discord.File(fp=BytesIO(img), filename="sinoalice.png")

        embed = discord.Embed(
            title=name,
            description=title,
            colour=0xfafafa)
        embed.set_image(url="attachment://sinoalice.png")
        embed.set_footer(text="SINoALICE")

        if reason and ctx.interaction:
            await ctx.send(f"{'gacha' if ctx.interaction.extras['rando'] else 'sinoalice'} {reason}:", embed=embed, file=file)
        else:
            await ctx.send(embed=embed, file=file)


    @commands.command(aliases=['touhou'])
    async def touhoulostword(self, ctx, reason: Optional[str] = None):
        await ctx.defer()

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
            await ctx.send(f"{'gacha' if ctx.interaction.extras['rando'] else 'touhou'} {reason}:", embed=embed)
        else:
            await ctx.send(embed=embed)


    @commands.command()
    async def worldflipper(self, ctx, reason: Optional[str] = None):
        await ctx.defer()

        url = ("https://api.github.com/repos/orbicube/worldflip/git/trees/"
            "da2abbedf7207fa36707017fe5ad841edd5556ca")
        headers = { "Authorization": f"Bearer {GITHUB_KEY}" }
        r = await self.bot.http_client.get(url, headers=headers)
        char = choice(r.json()["tree"])

        name, title = char["path"][:-4].split("#")
        if "_" in title:
            title = title.replace("_", ":")
        if "!" in title:
            title = title[:-1]

        r = await self.bot.http_client.get(char["url"], headers=headers)
        img = b64decode(r.json()["content"])
        file = discord.File(fp=BytesIO(img), filename="worldflipper.png")

        embed = discord.Embed(
            title=name,
            description=title,
            colour=0xb2d8ee)
        embed.set_image(url="attachment://worldflipper.png")
        embed.set_footer(text="World Flipper")

        if reason and ctx.interaction:
            await ctx.send(f"{'gacha' if ctx.interaction.extras['rando'] else 'World Flipper'} {reason}:", embed=embed, file=file)
        else:
            await ctx.send(embed=embed, file=file)


    @commands.command(aliases=['kof'])
    async def kofallstar(self, ctx, reason: Optional[str] = None):
        await ctx.defer()
   
        url = ("https://api.github.com/repos/orbicube/kofchars/git/trees/"
            "dad49f27c6cc4a766cfbb96c077bac925c146ee1")
        headers = { "Authorization": f"Bearer {GITHUB_KEY}" }
        r = await self.bot.http_client.get(url, headers=headers)
        char = choice(r.json()["tree"])

        name, game = char["path"][:-4].split("#")
        if game[0] == "'" or game[0] == "2" or game[0] == "X":
            game = f"The King of Fighters {game}"
        else:
            game_map = {
                "VF5FS": "Virtua Fighter 5 Final Showdown",
                "Samurai Shodown IV": "Samurai Shodown IV: Amakusa's Revenge",
                "SDS": "The Seven Deadly Sins", "AS": "",
                "GGXrd": "Guilty Gear Xrd REV 2", "SCVI": "Soulcalibur VI", 
                "WWE": "WWE", "TEKKEN 7": "TEKKEN 7", "Gintama": "Gintama",
                "SF6": "Street Fighter 6", "SFV": "Street Fighter V",
                "SevenKnights": "Seven Knights", "DoA6": "Dead or Alive 6"
            }
            game = game_map[game]

        r = await self.bot.http_client.get(char["url"], headers=headers)
        char_img = Image.open(BytesIO(b64decode(r.json()["content"])))
        char_img = char_img.crop(char_img.getbbox())

        with BytesIO() as img_binary:
            char_img.save(img_binary, 'PNG')
            img_binary.seek(0)
            file = discord.File(fp=img_binary, filename="kofas.png")

        embed = discord.Embed(
            title=name,
            description=game,
            colour=0xfc9a4c)
        embed.set_image(url="attachment://kofas.png")
        embed.set_footer(text="The King of Fighters ALLSTAR")

        if reason and ctx.interaction:
            await ctx.send(f"{'gacha' if ctx.interaction.extras['rando'] else 'kof'} {reason}:", embed=embed, file=file)
        else:
            await ctx.send(embed=embed, file=file)


    @commands.command(aliases=['404gamereset', '404'])
    async def errorgamereset(self, ctx, reason: Optional[str] = None):
        await ctx.defer()

        url = ("https://api.github.com/repos/orbicube/404chars/git/trees/"
            "58b9eb8f0c5e4ea34ec74b103d458458e788482e")
        headers = { "Authorization": f"Bearer {GITHUB_KEY}" }
        r = await self.bot.http_client.get(url, headers=headers)
        char = choice(r.json()["tree"])

        try:
            name, type = char["path"][:-4].split("#")
        except:
            name = char["path"][:-4]
            type = ""

        r = await self.bot.http_client.get(char["url"], headers=headers)
        img = b64decode(r.json()["content"])
        file = discord.File(fp=BytesIO(img), filename="404gamereset.png")

        embed = discord.Embed(
            title=name,
            description=type,
            colour=0x7f7f80)
        embed.set_image(url="attachment://404gamereset.png")
        embed.set_footer(text="404 GAME RE:SET")

        if reason and ctx.interaction:
            await ctx.send(f"{'gacha' if ctx.interaction.extras['rando'] else '404 game reset'} {reason}:", embed=embed, file=file)
        else:
            await ctx.send(embed=embed, file=file)


    @commands.command()
    async def bravefrontier(self, ctx, reason: Optional[str] = None):
        await ctx.defer()

        with open("ext/data/bfunits.txt", encoding="utf-8") as f:
            title = choice([line.rstrip() for line in f])

        url = "https://bravefrontierglobal.fandom.com/api.php"
        params = {
            "action": "parse",
            "page": title,
            "format": "json"
        }
        r = await self.bot.http_client.get(url,
            params=params, headers=self.headers)
        page = html.fromstring(r.json()["parse"]["text"]["*"].replace('\"','"'))

        img = page.xpath(
            "//div[@class='tabber wds-tabber']/div/div/center/span/a/@href")[0]

        embed = discord.Embed(
            title=title,
            colour=0xbfb135)
        embed.set_image(url=img)
        embed.set_footer(text="Brave Frontier")

        if reason and ctx.interaction:
            await ctx.send(f"{'gacha' if ctx.interaction.extras['rando'] else 'brave frontier'} {reason}:", embed=embed)
        else:
            await ctx.send(embed=embed)


    @commands.command()
    async def langrisser(self, ctx, reason: Optional[str] = None):
        await ctx.defer()
        
        url = "https://wiki.biligame.com/langrisser/api.php"

        with open("ext/data/langrisser.json", encoding="utf-8") as f:
            j = json.load(f)
        last_up = datetime.utcfromtimestamp(j["updated"])
        characters = j["characters"]
        if (datetime.utcnow() - last_up) / timedelta(weeks=1) > 1:
            params = {
                "action": "query",
                "list": "categorymembers",
                "cmtitle": "分类:英雄",
                "cmlimit": "500",
                "format": "json"
            }

            finished = False
            characters = []
            while not finished:
                r = await self.bot.http_client.get(url, 
                    params=params, headers=self.headers, timeout=15)
                results = r.json()

                if "continue" in results:
                    params["cmcontinue"] = results["continue"]["cmcontinue"]
                else:
                    finished = True

                for c in results["query"]["categorymembers"]:
                    if c["ns"] != 8:
                        characters.append(c["title"])

            data = {
                "updated": int(datetime.utcnow().timestamp()),
                "characters": characters
            }
            with open("ext/data/langrisser.json", "w", encoding="utf-8") as f:
                json.dump(data, f)                

        selected_article = choice(characters)
        params = {
            "action": "parse",
            "page": selected_article,
            "format": "json"
        }
        r = await self.bot.http_client.get(url,
            params=params, headers=self.headers, timeout=15)

        page = html.fromstring(
            r.json()["parse"]["text"]["*"].replace('\"','"'))

        name = page.xpath("//div[@class='HeroInfo_Name_EN']/text()")[0]
        skin = choice(
            page.xpath("//div[@class='HeroInfo_Skin_Img']/img/@src"))
        skin = skin.rsplit("/", 1)[0].replace("/thumb", "")

        r = await self.bot.http_client.get(skin, headers=self.headers, timeout=15)
        char_img = Image.open(BytesIO(r.content))
        char_img = char_img.crop(char_img.getbbox())

        with BytesIO() as img_binary:
            char_img.save(img_binary, 'PNG')
            img_binary.seek(0)
            file = discord.File(fp=img_binary, filename="langrisser.png")

        embed = discord.Embed(
            title=name,
            color=0xde181d)
        embed.set_image(url="attachment://langrisser.png")
        embed.set_footer(text="Langrisser")

        if reason and ctx.interaction:
            await ctx.send(f"{'gacha' if ctx.interaction.extras['rando'] else 'langrisser'} {reason}:", embed=embed, file=file)
        else:
            await ctx.send(embed=embed, file=file)


    @commands.command()
    async def cookierun(self, ctx, reason: Optional[str] = None):
        await ctx.defer()

        url = "https://cookierunkingdom.fandom.com/api.php"
        params = {
            "action": "query",
            "list": "categorymembers",
            "cmtitle": "Category:Playable_Cookies",
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

        img = page.xpath("//div[@class='pi-image-collection wds-tabber']/div/figure/a/@href")[0]

        embed = discord.Embed(
            title=selected_article,
            color=0xc0ab76)
        embed.set_image(url=img)
        embed.set_footer(text="Cookie Run: Kingdom")

        if reason and ctx.interaction:
            await ctx.send(f"{'gacha' if ctx.interaction.extras['rando'] else 'cookie run'} {reason}:", embed=embed)
        else:
            await ctx.send(embed=embed)


    @commands.command(aliases=['mmxd'])
    async def megamanxdive(self, ctx, reason: Optional[str] = None):
        await ctx.defer()

        url = "https://rockman-x-dive.fandom.com/api.php"
        params = {
            "action": "query",
            "list": "categorymembers",
            "cmtitle": "Category:Characters/Playable",
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

        img = page.xpath("//figure[@class='pi-item pi-image']/a/@href")[0]

        embed = discord.Embed(
            title=selected_article,
            color=0x1a7acb)
        embed.set_image(url=img)
        embed.set_footer(text="Mega Man X DiVE")

        if reason and ctx.interaction:
            await ctx.send(f"{'gacha' if ctx.interaction.extras['rando'] else 'mega man x dive'} {reason}:", embed=embed)
        else:
            await ctx.send(embed=embed)


    @commands.command(aliases=['saga'])
    async def romancingsaga(self, ctx, reason: Optional[str] = None):
        await ctx.defer()

        with open("ext/data/romancingsaga.json") as f:
            char = choice(json.load(f))

        embed = discord.Embed(
            title=char["name"],
            description=char["title"],
            color=0x8f0000)
        embed.set_image(url=f"https://rsrs.xyz/assets/gl/texture/style/{char['id']}/style_{char['id']}.png")
        embed.set_footer(text="Romancing SaGa re;univerSe")

        if reason and ctx.interaction:
            await ctx.send(f"{'gacha' if ctx.interaction.extras['rando'] else 'romancing saga re;universe'} {reason}:", embed=embed)
        else:
            await ctx.send(embed=embed)


    @commands.command(aliases=['ffbe', 'exvius'])
    async def braveexvius(self, ctx, reason: Optional[str] = None):
        await ctx.defer()

        url = "https://exvius.fandom.com/api.php"
        params = {
            "action": "query",
            "list": "categorymembers",
            "cmtitle": "Category:Units",
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

        await self.bot.get_channel(DEBUG_CHANNEL).send(
            f"ffbe {selected_article}")

        params = {
            "action": "parse",
            "page": selected_article,
            "format": "json"
        }
        r = await self.bot.http_client.get(url,
            params=params, headers=self.headers)
        page = html.fromstring(r.json()["parse"]["text"]["*"].replace('\"','"'))

        variant = choice(page.xpath("//table[@class='wikitable unit ibox']"))
        name = variant.xpath(".//tr[1]/th/text()")[0]
        img_url = variant.xpath(".//tr[2]/td/span/span/img/@data-image-key")[0]

        r = await self.bot.http_client.get(
            f"https://exvius.fandom.com/wiki/Special:FilePath/{img_url}",
            follow_redirects=True)
        char_img = Image.open(BytesIO(r.content))
        char_img = char_img.crop(char_img.getbbox())
        char_img = char_img.resize(
            (char_img.width*3, char_img.height*3),
            resample=0)

        with BytesIO() as img_binary:
            char_img.save(img_binary, 'PNG')
            img_binary.seek(0)
            file = discord.File(fp=img_binary, filename="braveexvius.png")

        embed = discord.Embed(
            title=name,
            color=0x9adafe)
        embed.set_image(url="attachment://braveexvius.png")
        embed.set_footer(text="Final Fantasy Brave Exvius")

        if reason and ctx.interaction:
            await ctx.send(f"{'gacha' if ctx.interaction.extras['rando'] else 'brave exvius'} {reason}:", embed=embed, file=file)
        else:
            await ctx.send(embed=embed, file=file)


    @commands.command(aliases=['bbdw'])
    async def blazblue(self, ctx, reason: Optional[str] = None):
        await ctx.defer()

        with open("ext/data/bbdw.json", encoding="utf-8") as f:
            char = choice(json.load(f))

        embed = discord.Embed(
            title=char["name"],
            color=0x4986c1)

        if char["title"]:
            embed.description = char["title"]

        embed.set_image(url=choice(char["art"]))
        embed.set_footer(text="BlazBlue Alternative: Dark War")

        if reason and ctx.interaction:
            await ctx.send(f"{'gacha' if ctx.interaction.extras['rando'] else 'blazblue dark war'} {reason}:", embed=embed)
        else:
            await ctx.send(embed=embed)


    @commands.command()
    async def umamusume(self, ctx, reason: Optional[str] = None):
        await ctx.defer()

        url = "https://umapyoi.net/api/v1/character"
        r = await self.bot.http_client.get(f"{url}/list")
        char = choice([c for c in r.json() if c["category_label_en"] != "Related parties"])

        r = await self.bot.http_client.get(f"{url}/images/{char['id']}")
        outfit = choice([o for o in r.json() if o["label_en"] == "Racewear"])

        r = await self.bot.http_client.get(outfit["images"][0]["image"])
        char_img = Image.open(BytesIO(r.content))
        char_img = char_img.crop(char_img.getbbox())

        with BytesIO() as img_binary:
            char_img.save(img_binary, 'PNG')
            img_binary.seek(0)
            file = discord.File(fp=img_binary, filename="umamusume.png")

        embed = discord.Embed(
            title = char["name_en"],
            color=0xd88da4)
        embed.set_image(url="attachment://umamusume.png")
        embed.set_footer(text="Umamusume: Pretty Derby")

        if reason and ctx.interaction:
            await ctx.send(f"{'gacha' if ctx.interaction.extras['rando'] else 'umamusume'} {reason}:", embed=embed, file=file)
        else:
            await ctx.send(embed=embed, file=file)


    @commands.command()
    async def afkarena(self, ctx, reason: Optional[str] = None):
        await ctx.defer()

        url = "https://afkarena.fandom.com/api.php"
        params = {
            "action": "query",
            "generator": "categorymembers",
            "prop": "vignetteimages",
            "gcmtitle": "Category:Heroes",
            "gcmnamespace": 0,
            "gcmlimit": "500",
            "format": "json"
        }
        finished = False
        char_list = []
        while not finished:
            r = await self.bot.http_client.get(url, 
                params=params, headers=self.headers)
            results = r.json()

            if "continue" in results:
                params["gcmcontinue"] = results["continue"]["gcmcontinue"]
            else:
                finished = True

            bad_pages = [85, 341, 966, 1971, 5566, 5568]
            for article in results["query"]["pages"].values():
                if article["pageid"] not in bad_pages and "pageimage" in article:
                    char_list.append(article)

        char = choice(char_list)

        embed = discord.Embed(
            color=0xd5a749)
        if " - " in char["title"]:
            name, title = char["title"].split(" - ")
            embed.description = title
        else:
            name = char["title"]
        embed.title = name

        r = await self.bot.http_client.get(
            f"https://afkarena.fandom.com/wiki/Special:FilePath/{char['pageimage']}",
            follow_redirects=True)

        char_img = Image.open(BytesIO(r.content))
        char_img = char_img.crop(char_img.getbbox())

        with BytesIO() as img_binary:
            char_img.save(img_binary, 'PNG')
            img_binary.seek(0)
            file = discord.File(fp=img_binary, filename=f"{char['pageimage']}")

        embed.set_image(
            url=f"attachment://{char['pageimage']}")
        embed.set_footer(text="AFK Arena")

        if reason and ctx.interaction:
            await ctx.send(f"{'gacha' if ctx.interaction.extras['rando'] else 'afk arena'} {reason}:", embed=embed, file=file)
        else:
            await ctx.send(embed=embed, file=file)


    @commands.command(aliases=['octopath', 'cotc'])
    async def octopathtraveler(self, ctx, reason: Optional[str] = None):
        await ctx.defer()

        url = ("https://api.github.com/repos/orbicube/octopath/git/trees/"
            "45fbdaeba65431cf1d82266138c662d9ebc2221b")
        headers = { "Authorization": f"Bearer {GITHUB_KEY}" }
        r = await self.bot.http_client.get(url, headers=headers)
        char = choice(r.json()["tree"])

        name = char["path"][:-4]
        title = ""
        if " EX" in name:
            title = "EX"
            name = name[:-3]

        r = await self.bot.http_client.get(char["url"], headers=headers)
        img = b64decode(r.json()["content"])
        file = discord.File(fp=BytesIO(img), filename="octopath.png")

        embed = discord.Embed(
            title=name,
            description=title,
            colour=0xcabf9e)
        embed.set_image(url="attachment://octopath.png")
        embed.set_footer(text="Octopath Traveler: Champions of the Continent")

        if reason and ctx.interaction:
            await ctx.send(f"{'gacha' if ctx.interaction.extras['rando'] else 'octopath'} {reason}:", embed=embed, file=file)
        else:
            await ctx.send(embed=embed, file=file)
 

    @commands.command()
    async def bravelydefault(self, ctx, reason: Optional[str] = None):
        await ctx.defer()

        url = ("https://api.github.com/repos/orbicube/bravelydefault/git/trees/"
            "5352a20a1f42bd3e80573201163ea212b65f8ebc")
        headers = { "Authorization": f"Bearer {GITHUB_KEY}" }
        r = await self.bot.http_client.get(url, headers=headers)

        char = choice(r.json()["tree"])
        name, title = char["path"][:-4].split("#")
        try:
            title_map = {"1star": "★", "3star": "★★★", "5star": "★★★★★"}
            name += f" {title_map[title]}"
            title = ""
        except:
            pass

        r = await self.bot.http_client.get(char["url"], headers=headers)
        char_img = Image.open(BytesIO(b64decode(r.json()["content"])))
        char_img = char_img.crop(char_img.getbbox())

        with BytesIO() as img_binary:
            char_img.save(img_binary, 'PNG')
            img_binary.seek(0)
            file = discord.File(fp=img_binary, filename="bravelydefault.png")

        embed = discord.Embed(
            title = name,
            description=title,
            color=0xb0c0b3)
        embed.set_image(url="attachment://bravelydefault.png")
        embed.set_footer(text="Bravely Default: Brilliant Lights")

        if reason and ctx.interaction:
            await ctx.send(f"{'gacha' if ctx.interaction.extras['rando'] else 'bravely default'} {reason}:", embed=embed, file=file)
        else:
            await ctx.send(embed=embed, file=file)


    @commands.command()
    async def echoesofmana(self, ctx, reason: Optional[str] = None):
        await ctx.defer()

        url = ("https://api.github.com/repos/orbicube/echoesofmana/git/trees/"
            "2a0b478efb52e81d9a6c490a448430e94676869c")
        headers = { "Authorization": f"Bearer {GITHUB_KEY}" }
        r = await self.bot.http_client.get(url, headers=headers)
        char = choice(r.json()["tree"])

        name, title = char["path"][:-4].split("#")
        if title == "Base":
            title = ""

        r = await self.bot.http_client.get(char["url"], headers=headers)
        char_img = Image.open(BytesIO(b64decode(r.json()["content"])))
        char_img = char_img.crop(char_img.getbbox())

        with BytesIO() as img_binary:
            char_img.save(img_binary, 'PNG')
            img_binary.seek(0)
            file = discord.File(fp=img_binary, filename=f"echoesofmana.png")

        embed = discord.Embed(
            title=name,
            description=title,
            colour=0xa6bbad)
        embed.set_image(url="attachment://echoesofmana.png")
        embed.set_footer(text="Echoes of Mana")

        if reason and ctx.interaction:
            await ctx.send(f"{'gacha' if ctx.interaction.extras['rando'] else 'Echoes of Mana'} {reason}:", embed=embed, file=file)
        else:
            await ctx.send(embed=embed, file=file)


    @commands.command(aliases=['soa'])
    async def starocean(self, ctx, reason: Optional[str] = None):
        await ctx.defer()

        with open("ext/data/starocean.json") as f:
            char = choice(json.load(f))
        variant = choice(char["variants"])

        embed = discord.Embed(
            title=char["name"],
            description=variant["title"],
            color=0x127799)

        r = await self.bot.http_client.get(f"https://starocean.fandom.com/wiki/Special:FilePath/{variant['img']}", follow_redirects=True)
        char_img = Image.open(BytesIO(r.content))
        char_img = char_img.crop(char_img.getbbox())

        with BytesIO() as img_binary:
            char_img.save(img_binary, 'PNG')
            img_binary.seek(0)
            file = discord.File(
                fp=img_binary,
                filename=variant['img'])

        embed.set_image(url=f"attachment://{variant['img']}")
        embed.set_footer(text="Star Ocean: Anamnesis")

        if reason and ctx.interaction:
            await ctx.send(f"{'gacha' if ctx.interaction.extras['rando'] else 'star ocean'} {reason}:", embed=embed, file=file)
        else:
            await ctx.send(embed=embed, file=file)


    @commands.command()
    async def nikke(self, ctx, reason: Optional[str] = None):
        await ctx.defer()

        url = "https://nikke-goddess-of-victory-international.fandom.com/"
        params = {
            "action": "query",
            "list": "categorymembers",
            "cmtitle": "Category:Playable_characters",
            "cmlimit": "500",
            "format": "json"
        }
        finished = False
        article_list = []
        while not finished:
            r = await self.bot.http_client.get(f"{url}api.php", 
                params=params, headers=self.headers)
            results = r.json()

            if "continue" in results:
                params["cmcontinue"] = results["continue"]["cmcontinue"]
            else:
                finished = True

            article_list.extend(results["query"]["categorymembers"])

        char = choice(article_list)["title"]
        await self.bot.get_channel(DEBUG_CHANNEL).send(f"nikke {char}")
        params = {
            "action": "parse",
            "page": char,
            "format": "json"
        }
        r = await self.bot.http_client.get(f"{url}api.php",
            params=params, headers=self.headers)
        page = html.fromstring(r.json()["parse"]["text"]["*"].replace('\"','"'))

        titles = page.xpath("//div[@class='pi-image-collection wds-tabber']/div/ul/li/span/text()")
        if titles:
            selected = randint(0, len(titles)-1)
        else:
            selected = 0
        title = ""
        if ": " in char:
            char, title = char.split(": ")
            if selected > 0:
                title = f"{title} ({titles[selected]})"
        elif selected > 0:
            title = titles[selected]

        img = page.xpath("//figure[@class='pi-item pi-image']/a/img/@data-image-key")[selected].replace('MI.p', 'FB.p').replace(' ', '_')
        r = await self.bot.http_client.get(url=f"{url}wiki/Special:FilePath/{img}", follow_redirects=True)

        char_img = Image.open(BytesIO(r.content))
        char_img = char_img.crop(char_img.getbbox())

        with BytesIO() as img_binary:
            char_img.save(img_binary, 'PNG')
            img_binary.seek(0)
            file = discord.File(fp=img_binary, filename=f"{img}")

        embed = discord.Embed(
            title=char,
            description=title,
            color=0xb4b3bb)
        embed.set_image(url=f"attachment://{img}")
        embed.set_footer(text="Goddess of Victory: Nikke")

        if reason and ctx.interaction:
            await ctx.send(f"{'gacha' if ctx.interaction.extras['rando'] else 'nikke'} {reason}:", embed=embed, file=file)
        else:
            await ctx.send(embed=embed, file=file)


    @commands.command(aliases=['msa'])
    async def metalslug(self, ctx, reason: Optional[str] = None):
        
        url = ("https://api.github.com/repos/orbicube/msa/git/trees/"
            "3dca6069518ed7ba82bc9e85e2547063689ba155")
        headers = { "Authorization": f"Bearer {GITHUB_KEY}" }
        r = await self.bot.http_client.get(url, headers=headers)

        char = choice(r.json()["tree"])
        try:
            name, title = char["path"][:-4].split("#")
        except:
            name = char["path"][:-4]
            title = ""

        r = await self.bot.http_client.get(char["url"], headers=headers)
        char_img = Image.open(BytesIO(b64decode(r.json()["content"])))
        char_img = char_img.crop(char_img.getbbox())

        with BytesIO() as img_binary:
            char_img.save(img_binary, 'PNG')
            img_binary.seek(0)
            file = discord.File(fp=img_binary, filename="metalslug.png")

        embed = discord.Embed(
            title = name,
            description=title,
            color=0xde8a39)
        embed.set_image(url="attachment://metalslug.png")
        embed.set_footer(text="Metal Slug Attack")

        if reason and ctx.interaction:
            await ctx.send(f"{'gacha' if ctx.interaction.extras['rando'] else 'metal slug'} {reason}:", embed=embed, file=file)
        else:
            await ctx.send(embed=embed, file=file)


    @commands.command()
    async def anothereden(self, ctx, reason: Optional[str] = None):
        await ctx.defer()

        url = "https://anothereden.wiki"
        params = {
            "action": "parse",
            "page": "Collection_Tracker",
            "format": "json"
        }
        r = await self.bot.http_client.get(f"{url}/api.php", params=params)
        page = html.fromstring(r.json()["parse"]["text"]["*"].replace('\"','"'))

        char = choice(page.xpath("//div[@class='tracker-item tracker-character']"))
        name = char.xpath(".//@data-name")[0]
        if " (" in name:
            name, title = name.split(" (")
            title = title[:-1]
        else:
            title = ""
        img = char.xpath(".//a/img/@src")[0][13:-9].replace("command", "base")
        r = await self.bot.http_client.get(
            f"https://anothereden.wiki/w/Special:FilePath/{img}",
            follow_redirects=True)

        char_img = Image.open(BytesIO(r.content))
        char_img = char_img.crop(char_img.getbbox())

        with BytesIO() as img_binary:
            char_img.save(img_binary, 'PNG')
            img_binary.seek(0)
            file = discord.File(fp=img_binary, filename=f"{img}")

        embed = discord.Embed(
            title=name,
            description=title,
            color=0x5e76af)
        embed.set_image(
            url=f"attachment://{img}")
        embed.set_footer(text="Another Eden")

        if reason and ctx.interaction:
            await ctx.send(f"{'gacha' if ctx.interaction.extras['rando'] else 'another eden'} {reason}:", embed=embed, file=file)
        else:
            await ctx.send(embed=embed, file=file)


    @commands.command()
    async def terrabattle(self, ctx, reason: Optional[str] = None):

        with open("ext/data/terrabattle.json") as f:
            chars = json.load(f)
            char = choice(list(chars.keys()))
        variant = choice(chars[char])

        embed = discord.Embed(
            title=char,
            description=variant["title"],
            color=0x648ba5)

        url = "https://terrabattle.fandom.com"
        if "Guardian_" in variant['img']:
            url = url.replace("e.f", "e2.f")
        url = f"{url}/wiki/Special:FilePath/{variant['img']}"
        r = await self.bot.http_client.get(url=url, follow_redirects=True)

        char_img = Image.open(BytesIO(r.content))
        char_img = char_img.crop(char_img.getbbox())

        with BytesIO() as img_binary:
            char_img.save(img_binary, 'PNG')
            img_binary.seek(0)
            file = discord.File(fp=img_binary, filename=f"{variant['img']}")
        embed.set_image(url=f"attachment://{variant['img']}")

        embed.set_footer(text=f"Terra Battle{' 2' if '2' in url else ' '}")

        if reason and ctx.interaction:
            await ctx.send(f"{'gacha' if ctx.interaction.extras['rando'] else 'terra battle'} {reason}:", embed=embed, file=file)
        else:
            await ctx.send(embed=embed, file=file)


    @commands.command(aliases=['ptn'])
    async def pathtonowhere(self, ctx, reason: Optional[str] = None):
        await ctx.defer()
        
        url = f"https://s1n.gg"

        with open("ext/data/ptn.json") as f:
            j = json.load(f)
        last_up = datetime.utcfromtimestamp(j["updated"])
        chars = j["chars"]

        if (datetime.utcnow() - last_up) / timedelta(weeks=1) > 2:
            r = await self.bot.http_client.get(url)
            page = html.fromstring(r.text)
            js_url = page.xpath("//script[@type='module']/@src")[0]

            r = await self.bot.http_client.get(f"{url}{js_url}")
            apikey = re.findall(r'base.co",\w+="([^"]+)"', r.text)[0]
            char_list = re.findall(r'{id:"(\w+)",name:"([^"]+)",imgAv', r.text)

            chars = {}
            for char in char_list:
                chars[char[1]] = {"id": char[0], "outfits": []}

            at_url = f"https://qcropwcwnvrflrzlsucj.supabase.co/rest/v1/attires"
            r = await self.bot.http_client.get(at_url,
                params={"select": "img,name,sinner"},
                headers={"apikey": apikey})

            for outfit in r.json():
                if "!Chief" not in outfit["sinner"]:
                    outfit["sinner"] = outfit["sinner"].replace("Zero", "000")
                    chars[outfit["sinner"]]["outfits"].append({
                        "title": outfit["name"],
                        "url": outfit["img"]})

            data = {
                "updated": int(datetime.utcnow().timestamp()),
                "chars": chars
            }
            with open("ext/data/ptn.json", "w") as f:
                json.dump(data, f)
                
        char = choice(list(chars.keys()))

        r = await self.bot.http_client.get(f"{url}/data/sinners/{chars[char]['id']}.json")
        char_data = r.json()

        char_outfits = chars[char]["outfits"]
        char_outfits.append({
            "title": "",
            "url": char_data["imgBase"]})
        char_outfits.append({
            "title": "",
            "url": char_data["imgPhaseup"]})

        variant = choice(char_outfits)
        await self.bot.get_channel(DEBUG_CHANNEL).send(f"ptn <{variant['url']}>")

        embed = discord.Embed(
            title=char,
            description=variant["title"],
            color=0xa21f23)

        r = await self.bot.http_client.get(variant["url"], headers=self.headers)

        char_img = Image.open(BytesIO(r.content))
        char_img = char_img.crop(char_img.getbbox())

        with BytesIO() as img_binary:
            char_img.save(img_binary, 'PNG')
            img_binary.seek(0)
            file = discord.File(fp=img_binary, filename=f"{chars[char]['id']}.png")

        embed.set_image(url=f"attachment://{chars[char]['id']}.png")
        embed.set_footer(text="Path to Nowhere")

        if reason and ctx.interaction:
            await ctx.send(f"{'gacha' if ctx.interaction.extras['rando'] else 'path to nowhere'} {reason}:", embed=embed, file=file)
        else:
            await ctx.send(embed=embed, file=file)


    @commands.command(aliases=['p5x'])
    async def persona5x(self, ctx, reason: Optional[str] = None):
        await ctx.defer()

        url = "https://lufel.net/"

        with open("ext/data/p5x.json", encoding="utf-8") as f:
            j = json.load(f)
        last_up = datetime.utcfromtimestamp(j["updated"])
        characters = j["characters"]
        if (datetime.utcnow() - last_up) / timedelta(weeks=1) > 3:
            r = await self.bot.http_client.get(
                f"{url}data/kr/characters/characters.js")
            temp_dict = r.text.split("characterData = ")[1].split("},", 1)[1][:-2]
            temp_dict = "{\n" + temp_dict.replace(',\n    },', '\n    },')
            temp_dict = temp_dict.replace(',\n        },', '\n        },')
            temp_dict = temp_dict.replace('},\n\n    ', '},\n     ')

            char_dict = json.loads(temp_dict)
            characters = []
            for key in list(char_dict.keys()):
                if "persona3" in char_dict[key]:
                    title = "S.E.E.S."
                else:
                    title = char_dict[key]["codename"].title()

                new_char = {
                    "key": key,
                    "name": char_dict[key]["name_en"],
                    "title": title
                }
                
                characters.append(new_char)

            data = {
                "updated": int(datetime.utcnow().timestamp()),
                "characters": characters
            }
            with open("ext/data/p5x.json", "w", encoding="utf-8") as f:
                json.dump(data, f)

        char = choice(characters)

        embed = discord.Embed(
            title=char["name"],
            description= char["title"],
            color=0xf30002)

        r = await self.bot.http_client.get(
            f"{url}assets/img/character-detail/{char['key']}.webp")
        char_img = Image.open(BytesIO(r.content))
        char_img = char_img.crop(char_img.getbbox())

        with BytesIO() as img_binary:
            char_img.save(img_binary, 'PNG')
            img_binary.seek(0)
            file = discord.File(
                fp=img_binary,
                filename=f"{char['name'].replace(' ', '')}.png")

        embed.set_image(url=f"attachment://{char['name'].replace(' ', '')}.png")
        embed.set_footer(text="Persona 5: The Phantom X")

        if reason and ctx.interaction:
            await ctx.send(f"{'gacha' if ctx.interaction.extras['rando'] else 'persona 5 x'} {reason}:", embed=embed, file=file)
        else:
            await ctx.send(embed=embed, file=file)


    @commands.command(aliases=['genshin'])
    async def genshinimpact(self, ctx, reason: Optional[str] = None):
        await ctx.defer()

        url = "https://genshin-impact.fandom.com"
        params = {
            "action": "parse",
            "page": "Wish/Gallery",
            "format": "json"
        }
        r = await self.bot.http_client.get(f"{url}/api.php", params=params)
        page = html.fromstring(r.json()["parse"]["text"]["*"].replace('\"','"'))

        char = choice(
            page.xpath("//div[@id='gallery-3']/div[@class='wikia-gallery-item']"))

        char_name = char.xpath(".//div[@class='lightbox-caption']/a/text()")[0]
        img_url = char.xpath(".//div[@class='thumb']/div/a/@href")[0].replace("/File:", "/Special:FilePath/")

        embed = discord.Embed(
            title=char_name,
            color=0xa4ec93)

        r = await self.bot.http_client.get(f"{url}{img_url}", follow_redirects=True)
        char_img = Image.open(BytesIO(r.content))
        char_img = char_img.crop(char_img.getbbox())

        with BytesIO() as img_binary:
            char_img.save(img_binary, 'PNG')
            img_binary.seek(0)
            file = discord.File(
                fp=img_binary,
                filename=img_url.split("Path/")[1])

        embed.set_image(url=f"attachment://{img_url.split('Path/')[1]}")
        embed.set_footer(text="Genshin Impact")

        if reason and ctx.interaction:
            await ctx.send(f"{'gacha' if ctx.interaction.extras['rando'] else 'genshin impact'} {reason}:", embed=embed, file=file)
        else:
            await ctx.send(embed=embed, file=file)


    @commands.command(aliases=['hsr'])
    async def honkaistarrail(self, ctx, reason: Optional[str] = None):
        await ctx.defer()

        url = "https://honkai-star-rail.fandom.com/api.php"
        params = {
            "action": "query",
            "generator": "categorymembers",
            "prop": "vignetteimages",
            "gcmtitle": "Category:Playable_Characters",
            "gcmnamespace": 0,
            "gcmlimit": "500",
            "format": "json"
        }
        finished = False
        char_list = []
        while not finished:
            r = await self.bot.http_client.get(url, 
                params=params, headers=self.headers)
            results = r.json()

            if "continue" in results:
                params["gcmcontinue"] = results["continue"]["gcmcontinue"]
            else:
                finished = True

            bad_pages = []
            for article in results["query"]["pages"].values():
                if article["pageid"] not in bad_pages and "pageimage" in article:
                    char_list.append(article)

        char = choice(char_list)

        embed = discord.Embed(
            title=char["title"],
            color=0x648fb8)

        r = await self.bot.http_client.get(
            f"https://honkai-star-rail.fandom.com/wiki/Special:FilePath/{char['pageimage']}",
            follow_redirects=True)

        char_img = Image.open(BytesIO(r.content))
        char_img = char_img.crop(char_img.getbbox())

        with BytesIO() as img_binary:
            char_img.save(img_binary, 'PNG')
            img_binary.seek(0)
            file = discord.File(fp=img_binary, filename=f"{char['pageimage']}")

        embed.set_image(
            url=f"attachment://{char['pageimage']}")
        embed.set_footer(text="Honkai Star Rail")

        if reason and ctx.interaction:
            await ctx.send(f"{'gacha' if ctx.interaction.extras['rando'] else 'honkai star rail'} {reason}:", embed=embed, file=file)
        else:
            await ctx.send(embed=embed, file=file)


    @commands.command(aliases=['zzz'])
    async def zenlesszonezero(self, ctx, reason: Optional[str] = None):
        await ctx.defer()

        url = "https://zenless-zone-zero.fandom.com/api.php"
        params = {
            "action": "query",
            "generator": "categorymembers",
            "prop": "vignetteimages",
            "gcmtitle": "Category:Playable_Agents",
            "gcmnamespace": 0,
            "gcmlimit": "500",
            "format": "json"
        }
        finished = False
        char_list = []
        while not finished:
            r = await self.bot.http_client.get(url, 
                params=params, headers=self.headers)
            results = r.json()

            if "continue" in results:
                params["gcmcontinue"] = results["continue"]["gcmcontinue"]
            else:
                finished = True

            bad_pages = []
            for article in results["query"]["pages"].values():
                if article["pageid"] not in bad_pages and "pageimage" in article:
                    char_list.append(article)

        char = choice(char_list)

        embed = discord.Embed(
            title=char["title"],
            color=0xb9d600)

        r = await self.bot.http_client.get(
            f"https://zenless-zone-zero.fandom.com/wiki/Special:FilePath/{char['pageimage']}",
            follow_redirects=True)

        char_img = Image.open(BytesIO(r.content))
        char_img = char_img.crop(char_img.getbbox())

        with BytesIO() as img_binary:
            char_img.save(img_binary, 'PNG')
            img_binary.seek(0)
            file = discord.File(fp=img_binary, filename=f"{char['pageimage']}")

        embed.set_image(
            url=f"attachment://{char['pageimage']}")
        embed.set_footer(text="Zenless Zone Zero")

        if reason and ctx.interaction:
            await ctx.send(f"{'gacha' if ctx.interaction.extras['rando'] else 'zenless zone zero'} {reason}:", embed=embed, file=file)
        else:
            await ctx.send(embed=embed, file=file)


    @commands.command()
    async def dislyte(self, ctx, reason: Optional[str] = None):
        await ctx.defer()

        url = "https://dislyte.fandom.com/"
        params = {
            "action": "query",
            "list": "categorymembers",
            "cmtitle": "Category:Esper_galleries",
            "cmlimit": "500",
            "format": "json"
        }
        finished = False
        article_list = []
        while not finished:
            r = await self.bot.http_client.get(f"{url}api.php", 
                params=params, headers=self.headers)
            results = r.json()

            if "continue" in results:
                params["cmcontinue"] = results["continue"]["cmcontinue"]
            else:
                finished = True

            article_list.extend(results["query"]["categorymembers"])

        char = choice(article_list)["title"]
        char_name, char_deity = char.split(")/")[0].split(" (")
        params = {
            "action": "parse",
            "page": char,
            "format": "json"
        }
        r = await self.bot.http_client.get(f"{url}api.php",
            params=params, headers=self.headers)
        page = html.fromstring(r.json()["parse"]["text"]["*"].replace('\"','"'))
        skin = choice(page.xpath(
            "//div/table[@class='dis-atable']"))
        skin_name = skin.xpath("//tbody/tr[1]/th/text()")[0]

        embed = discord.Embed(
            title=char_name,
            color=0xadebe3)
        embed.set_author(name=char_deity)
        if "Default" not in skin_name:
            embed.description = skin_name

        char_url = skin.xpath(
            "//tbody/tr[2]/td/figure/a/img/@data-image-key")[0]
        r = await self.bot.http_client.get(
            f"{url}wiki/Special:FilePath/{char_url}", follow_redirects=True)

        char_img = Image.open(BytesIO(r.content))
        char_img = char_img.crop(char_img.getbbox())

        with BytesIO() as img_binary:
            char_img.save(img_binary, 'PNG')
            img_binary.seek(0)
            file = discord.File(fp=img_binary, filename=char_url)

        embed.set_image(
            url=f"attachment://{char_url}")
        embed.set_footer(text="Dislyte")

        if reason and ctx.interaction:
            await ctx.send(f"{'gacha' if ctx.interaction.extras['rando'] else 'dislyte'} {reason}:", embed=embed, file=file)
        else:
            await ctx.send(embed=embed, file=file)


    @commands.command(aliases=['ff7ec'])
    async def evercrisis(self, ctx, reason: Optional[str] = None):
        await ctx.defer()

        url = "https://finalfantasy.fandom.com/"
        params = {
            "action": "parse",
            "page": "Final Fantasy VII Ever Crisis gear",
            "format": "json"
        }
        r = await self.bot.http_client.get(f"{url}api.php",
            params=params, headers=self.headers)
        page = html.fromstring(r.json()["parse"]["text"]["*"].replace('\"','"'))

        skin = choice(page.xpath("//img[not(@alt='Userbox ff7-barret')]"))
        char_url = skin.xpath("./@data-image-key")[0]
        char_name = skin.xpath(
            "./ancestor::table/preceding::h3[1]/span/a/text()")[0]
        char_title = skin.xpath("./ancestor::tr/td[2]/span/text()")[0]

        embed = discord.Embed(
            title=char_name,
            description=char_title,
            color=0xe9d7b5)

        r = await self.bot.http_client.get(
            f"{url}wiki/Special:FilePath/{char_url}", follow_redirects=True)

        char_img = Image.open(BytesIO(r.content))
        char_img = char_img.crop(char_img.getbbox())

        with BytesIO() as img_binary:
            char_img.save(img_binary, 'PNG')
            img_binary.seek(0)
            file = discord.File(fp=img_binary, filename=char_url)

        embed.set_image(
            url=f"attachment://{char_url}")
        embed.set_footer(text="Final Fantasy VII Ever Crisis")

        if reason and ctx.interaction:
            await ctx.send(f"{'gacha' if ctx.interaction.extras['rando'] else 'ever crisis'} {reason}:", embed=embed, file=file)
        else:
            await ctx.send(embed=embed, file=file)



    @commands.command()
    async def foodfantasy(self, ctx, reason: Optional[str] = None):
        await ctx.defer()

        url = "https://food-fantasy.fandom.com/"
        params = {
            "action": "query",
            "list": "categorymembers",
            "cmtitle": "Category:Food_Souls",
            "cmlimit": "500",
            "format": "json"
        }
        finished = False
        article_list = []
        while not finished:
            r = await self.bot.http_client.get(f"{url}api.php", 
                params=params, headers=self.headers)
            results = r.json()

            if "continue" in results:
                params["cmcontinue"] = results["continue"]["cmcontinue"]
            else:
                finished = True

            bad_pages = [4585, 1752, 29713, 143]

            for article in results["query"]["categorymembers"]:
                if article["ns"] == 0 and article["pageid"] not in bad_pages:
                    article_list.append(article)

        char = choice(article_list)["title"]
        params = {
            "action": "parse",
            "page": char,
            "format": "json"
        }
        r = await self.bot.http_client.get(f"{url}api.php",
            params=params, headers=self.headers)
        page = html.fromstring(r.json()["parse"]["text"]["*"].replace('\"','"'))
        sections = page.xpath("//aside/section[1]/div")

        skin_count = len(sections) - 1
        selected_skin = randint(1, skin_count)

        skin_name = sections[0].xpath(
            f"./ul/li[{selected_skin}]/div/text()")[0].strip()
        if skin_name == "Basic":
            skin_name = ""
        if "(SP)" in char:
            if skin_name:
                skin_name = "SP " + skin_name
            else:
                skin_name = "SP"

            char = char.split(" (")[0]

        embed = discord.Embed(
            title=char,
            description=skin_name,
            color=0xf6be41)

        char_url = sections[selected_skin].xpath(
            "./div[1]/div/span/a/img/@data-image-key")[0].replace("jpg", "png")
        r = await self.bot.http_client.get(
            f"{url}wiki/Special:FilePath/{char_url}", follow_redirects=True)

        char_img = Image.open(BytesIO(r.content))
        char_img = char_img.crop(char_img.getbbox())

        with BytesIO() as img_binary:
            char_img.save(img_binary, 'PNG')
            img_binary.seek(0)
            file = discord.File(fp=img_binary, filename=char_url)

        embed.set_image(
            url=f"attachment://{char_url}")
        embed.set_footer(text="Food Fantasy")

        if reason and ctx.interaction:
            await ctx.send(f"{'gacha' if ctx.interaction.extras['rando'] else 'food fantasy'} {reason}:", embed=embed, file=file)
        else:
            await ctx.send(embed=embed, file=file)


    @commands.command()
    async def resonancesolstice(self, ctx, reason: Optional[str] = None):
        await ctx.defer()

        url = "https://wiki.biligame.com/resonance/api.php"

        with open("ext/data/resosol.json", encoding="utf-8") as f:
            j = json.load(f)
        last_up = datetime.utcfromtimestamp(j["updated"])
        characters = j["characters"]
        if (datetime.utcnow() - last_up) / timedelta(weeks=1) > 1:
            params = {
                "action": "query",
                "list": "categorymembers",
                "cmtitle": "分类:乘员",
                "cmlimit": "500",
                "format": "json"
            }

            finished = False
            characters = []
            while not finished:
                r = await self.bot.http_client.get(url, 
                    params=params, headers=self.headers, timeout=15)
                results = r.json()

                if "continue" in results:
                    params["cmcontinue"] = results["continue"]["cmcontinue"]
                else:
                    finished = True

                for c in results["query"]["categorymembers"]:
                    if c["ns"] != 8:
                        characters.append(c["title"])

            data = {
                "updated": int(datetime.utcnow().timestamp()),
                "characters": characters
            }
            with open("ext/data/resosol.json", "w", encoding="utf-8") as f:
                json.dump(data, f)                

        selected_article = choice(characters)
        params = {
            "action": "parse",
            "page": selected_article,
            "format": "json"
        }
        r = await self.bot.http_client.get(url,
            params=params, headers=self.headers, timeout=15)
        page = html.fromstring(
            r.json()["parse"]["text"]["*"].replace('\"','"'))
        info = page.xpath("//div[@class='resp-tab-content'][1]/div")[0]

        char = info.xpath("./div[@class='rh-info']/div[2]/div[2]/text()")[0]

        embed = discord.Embed(
            title=char,
            color=0x3f4149)

        char_url = info.xpath("./div[@class='rh-portrait']/img/@src")[0]
        r = await self.bot.http_client.get(
            char_url, headers=self.headers, timeout=15)
        char_img = Image.open(BytesIO(r.content))
        char_img = char_img.crop(char_img.getbbox())

        with BytesIO() as img_binary:
            char_img.save(img_binary, 'PNG')
            img_binary.seek(0)
            file = discord.File(fp=img_binary, filename="resonancesolstice.png")

        embed.set_image(url="attachment://resonancesolstice.png")
        embed.set_footer(text="Resonance Solstice")

        if reason and ctx.interaction:
            await ctx.send(f"{'gacha' if ctx.interaction.extras['rando'] else 'resonance solstice'} {reason}:", embed=embed, file=file)
        else:
            await ctx.send(embed=embed, file=file)


async def setup(bot):
    await bot.add_cog(Gacha(bot))