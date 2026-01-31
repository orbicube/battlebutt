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

import asyncio

from credentials import DEBUG_CHANNEL, FNAPI_KEY, GITHUB_KEY, ERROR_CHANNEL

class Gacha(commands.Cog,
    command_attrs={"cooldown": commands.CooldownMapping.from_cooldown(
        2, 15, commands.BucketType.user)}):

    headers = {
        "User-Agent": "battlebutt/1.0"
    }

    def __init__(self, bot):
        self.bot = bot
        self.file_regex = re.compile(
            r'[^\/\\&\?]+\.\w{2,4}(?=(?:[\?&\/].*$|$))')

    @commands.hybrid_command()
    @app_commands.describe(game="Gacha you want to pull a character from")
    async def gacha(self, ctx, game: Optional[str] = None,
        reason: Optional[str] = None):
        """ Pulls a character from a gacha game """

        commands = [c for c in self.get_commands() if "gacha" not in c.name]

        selected_comm = next((
            c for c in commands if c.name == game or game in c.aliases), None)

        if ctx.interaction:
            ctx.interaction.extras = {"random": False}

            if reason:
                ctx.interaction.extras["reason"] = reason

        if not selected_comm:
            selected_comm = choice(commands)

            await self.bot.get_channel(DEBUG_CHANNEL).send(
                f"{selected_comm.name}")
            
            if ctx.interaction:
                ctx.interaction.extras["random"] = True

        await selected_comm.__call__(ctx)


    @gacha.autocomplete('game')
    async def gacha_autocomplete(self, interaction: discord.Interaction,
        current: str,) -> list[app_commands.Choice[str]]:

        games = [c.name for c in self.get_commands() if not c.name == "gacha"]
        completes = [app_commands.Choice(name=game, value=game)
            for game in games if current.lower() in game.lower()]

        if not current:
            completes = sample(completes, len(completes))

        return completes[:25]


    @commands.command(hidden=True)
    @commands.is_owner()
    async def gacha_test(self, ctx, start_from: Optional[str] = None):

        commands = self.get_commands()
        for c in commands:
            if "gacha" not in c.name:
                await ctx.send(f"Calling {c.name}:")
                await c.__call__(ctx)

                await asyncio.sleep(2)


    async def post(self, ctx: commands.Context, img: discord.File|str,
        game_name: str, color: int, char_name: str, description: str = None,
        game_short: str = None, author: str = None):

        embed = discord.Embed(
            title=char_name,
            description=description,
            color=color)

        if author:
            embed.set_author(name=author)

        embed.set_footer(text=game_name)

        msg = ""
        try:
            reason = ctx.interaction.extras["reason"]

            if ctx.interaction.extras["random"]:
                game_short = "gacha"
            elif not game_short:
                game_short = game_name.lower()

            msg = f"{game_short} {reason}:"
        except:
            pass

        if isinstance(img, str):
            embed.set_image(url=img)
            await ctx.send(msg, embed=embed)
        else:
            embed.set_image(url=img.uri)
            await ctx.send(msg, embed=embed, file=img)


    async def url_to_file(self, url: str, filename: str = None, 
        headers: dict = None, resize: float = 0, resample: bool = False):

        if not filename:
            filename = self.file_regex.findall(url)[1]

        if not headers:
            headers = self.headers

        r = await self.bot.http_client.get(url=url, headers=headers,
            follow_redirects=True)

        if 'application/json' in r.headers.get('Content-Type', ''):
            img = Image.open(BytesIO(b64decode(r.json()["content"])))
        else:
            img = Image.open(BytesIO(r.content))
        img_format = img.format

        img = img.crop(img.getbbox())

        if resize > 0.0:
            img = img.resize(
                (img.width*resize, img.height*resize),
                resample=resample)

        with BytesIO() as img_binary:
            img.save(img_binary, img_format)
            img_binary.seek(0)
            file = discord.File(fp=img_binary, filename=filename)

        return file


    async def get_github(self, repo: str, tree: str):

        url = f"https://api.github.com/repos/{repo}/git/trees/{tree}"
        headers = { "Authorization": f"Bearer {GITHUB_KEY}" }

        r = await self.bot.http_client.get(url, headers=headers)
        char = choice(r.json()["tree"])

        file = await self.url_to_file(url=char["url"],
            filename=char["path"], headers=headers)

        return file, char["path"]


    async def get_imageinfo(self, url, filename,
        reize=0.0, resample=False):
        params = {
            "action": "query",
            "prop": "imageinfo",
            "titles": f"File:{filename}",
            "format": "json",
            "iiprop": "url"
        }

        r = await self.bot.http_client.get(url=url,
            params=params, headers=self.headers)

        results = list(r.json()["query"]["pages"].values())
        img = results[0]["imageinfo"][0]["url"]

        return await self.url_to_file(img)


    async def mediawiki_parse(self, url, page):

        params = {
            "action": "parse",
            "page": page,
            "format": "json"
        }
        r = await self.bot.http_client.get(url, params=params,
            headers=self.headers, timeout=15)

        page = html.fromstring(
            r.json()["parse"]["text"]["*"].replace('\"','"'))

        return page


    async def mediawiki_category(self, url: str, category: str, 
        bad_pages: list = [], vignette: bool = False):
        
        params = {
            "action": "query",
            "format": "json"
        }
        if vignette:
            params["generator"] = "categorymembers"
            params["prop"] = "vignetteimages"
            params["gcmtitle"] = category
            params["gcmnamespace"] = 0
            params["gcmlimit"] = "500"
            cont_key = "gcmcontinue"
        else:
            params["list"] = "categorymembers"
            params["cmtitle"] = category
            params["cmlimit"] = "500"
            cont_key = "cmcontinue"

        finished = False
        article_list = []
        while not finished:
            r = await self.bot.http_client.get(url, 
                params=params, headers=self.headers,
                follow_redirects=True)
            results = r.json()

            if "continue" in results:
                params[cont_key] = results["continue"][cont_key]
            else:
                finished = True

            if vignette:
                for page in results["query"]["pages"].values():
                    if page["pageid"] not in bad_pages:
                        if "pageimage" in page:
                            article_list.append(page)
            else:
                for article in results["query"]["categorymembers"]:
                    if article["pageid"] not in bad_pages:
                        if article["ns"] == 0:
                            article_list.append(article)

        return article_list


    def check_cache(self, filename: str):
        try:            
            with open(f"ext/data/gacha/{filename}.json",
                encoding="utf-8") as f:
                j = json.load(f)
        except:
            return []

        last_up = datetime.utcfromtimestamp(j["updated"])
        if (datetime.utcnow() - last_up) / timedelta(weeks=1) > 3:
            if "bad_pages" in j.keys():
                return None, j["bad_pages"]
            else:
                return None
        else:
            if "bad_pages" in j.keys():
                return j["characters"], j["bad_pages"]
            return j["characters"]


    def write_cache(self, filename: str,
        characters: list, bad_pages: list = []):

        data = {
            "updated": int(datetime.utcnow().timestamp()),
            "characters": characters
        }

        if bad_pages:
            data["bad_pages"] = bad_pages

        with open(f"ext/data/gacha/{filename}.json", "w",
            encoding="utf-8") as f:
            json.dump(data, f)


    @commands.command(aliases=['gbf'], hidden=True)
    async def granblue(self, ctx):
        await ctx.defer()

        characters = self.check_cache("gbf")
        if not characters:
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

            self.write_cache("gbf", characters)

        char = choice(characters)
        img = choice(char['arts'])

        file = await self.url_to_file(
            f"https://gbf.wiki/Special:FilePath/{img}")

        await self.post(ctx, file, "Granblue Fantasy", 0x1ca6ff,
            char["name"], char["title"], "granblue")


    @commands.command(aliases=['feh'])
    async def fireemblem(self, ctx):    
        await ctx.defer()
        url = f"https://feheroes.fandom.com/api.php"

        characters = await self.mediawiki_category(url,
            "Category:Heroes")
        char = choice(characters)["title"]

        await self.bot.get_channel(DEBUG_CHANNEL).send(f"feh {char}")

        page = await self.mediawiki_parse(url, char)

        img = choice(page.xpath(
            "//div[@class='fehwiki-tabber']/span/a[1]/@href"))

        file = await self.url_to_file(img)

        await self.post(ctx, file, "Fire Emblem Heroes", 0xc3561f,
            char.split(":")[0], char.split(": ")[1])


    @commands.command(aliases=['wotv'])
    async def warofthevisions(self, ctx):
        await ctx.defer()
        url = "https://wotv-calc.com/api/gl/units?forBuilder=1"

        headers = self.headers
        headers["Referer"] = "https://wotv-calc.com/builder/unit"
        r = await self.bot.http_client.get(url, headers=headers)

        char = choice(r.json())
        img = f"https://wotv-calc.com/assets/units/{char['image']}.webp"

        await self.post(ctx, img,
            "War of the Visions: Final Fantasy Brave Exvius",
            0x2c4584, char["names"]["en"], game_short="war of the visions")


    @commands.command()
    async def arknights(self, ctx):
        await ctx.defer()
        base_url = "https://raw.githubusercontent.com/Aceship"

        url = (f"{base_url}/AN-EN-Tags/refs/heads/master/json/gamedata/"
            f"en_US/gamedata/excel/skin_table.json")
        r = await self.bot.http_client.get(url)

        skins = r.json()["charSkins"]
        selected_skin = choice(
            [skin for skin in skins.keys() if "char_" in skin])
        skin_file = skins[selected_skin]['portraitId'].replace('#','%23')

        img_url = (f"{base_url}/Arknight-Images/refs/heads/main/"
            f"characters/{skin_file}.png")

        await self.post(ctx, img_url, "Arknights", 0xfcda16,
            skins[selected_skin]["displaySkin"]["modelName"])


    @commands.command()
    async def dragalialost(self, ctx):
        await ctx.defer()

        file, char_path = await self.get_github("orbicube/draglost",
            "fd97dddadcc4347e5b98dd9e747f6a6bc9b430cd")

        name, title = char_path[:-4].split("#")

        await self.post(ctx, file, "Dragalia Lost", 0x3e91f1, name, title)


    @commands.command(aliases=['mkt'])
    async def mariokarttour(self, ctx):
        await ctx.defer()
        url = "https://www.mariowiki.com/api.php"

        page = await self.mediawiki_parse(url,
            "Gallery:Mario_Kart_Tour_sprites_and_models")

        characters = page.xpath(
            "//span[@id='In-game_portraits']/../following-sibling::ul[1]/li")
        character = choice(characters)

        name = character.xpath(".//div/p/a/text()")[0]
        title = ""
        if " (" in name:
            name, title = name.rsplit(" (", 1)
            title = title[:-1] 

        img = character.xpath(".//a[@class='image']/img/@src")[0].rsplit(
            "/", 1)[0].replace('/thumb', '')

        await self.post(ctx, img, "Mario Kart Tour", 0xe60012, name, title)


    @commands.command()
    async def fortnite(self, ctx):
        await ctx.defer()
        url = f"https://fortnite.fandom.com/api.php"

        characters, bad_pages = self.check_cache("fortnite")
        if not characters:
            characters = await self.mediawiki_category(url,
                "Category:Outfits")

            self.write_cache("fortnite", characters, bad_pages)

        char = choice(characters)

        page = await self.mediawiki_parse(url, char["title"])

        images = page.xpath("//aside//img[@class='pi-image-thumbnail']")

        featured = []
        for image in images:
            img_url = image.xpath("../@href")[0]
            if "Featured%29" in img_url or "Pass%29" in img_url:
                featured.append(img_url)

        if not featured:
            raise ValueError((
                "No featured image found, potentially bad page: "
                f"{char['title']} (ID: {char['pageid']})"))

        if " (Outfit)" in char["title"]:
            char["title"] = char["title"][:-9]

        img = choice(featured)
        file = await self.url_to_file(img)

        await self.post(ctx, file, "Fortnite", 0xad2fea, char["title"])


    @commands.command(aliases=['fgo'])
    async def fategrandorder(self, ctx):
        await ctx.defer()
        url = f"https://fategrandorder.fandom.com/api.php"

        bad_pages = [24917, 64670, 383442, 111081, 579165, 623674, 603920,
            602461, 658001, 123993, 34471, 34468, 631866, 6665513, 78799,
            509030, 663419, 635637, 671627, 635810, 640684, 565396, 602786,
            410778, 124402, 253574, 666612, 603989, 670436, 547889, 410804,
            78805, 8077, 674121, 292832, 576046, 26980, 74218, 633911, 
            585580, 650647, 34469, 644422, 34470]

        chars = await self.mediawiki_category(url, 
            "Category:Servant", bad_pages=bad_pages)
        char = choice(chars)["title"]
        await self.bot.get_channel(DEBUG_CHANNEL).send(f"fgo {char}")

        page = await self.mediawiki_parse(url=url, page=char)

        images = page.xpath(("//div[@class='pi-image-collection wds-tabber']"
            "/div[@class='wds-tab__content']/figure/a/@href"))
        img = choice([i for i in images if 'Sprite' not in i])

        file = await self.url_to_file(img)

        await self.post(ctx, file, "Fate/Grand Order", 0xece9d6, char)


    @commands.command(aliases=['nier'])
    async def nierreincarnation(self, ctx):
        await ctx.defer()

        file, char_path = await self.get_github("orbicube/nierrein",
            "a5010db7dc892bf89feda0bb305e3f9bc5538858")

        name, title = char_path[:-4].split("#")

        await self.post(ctx, file, "NieR Re[in]carnation", 0x3b70c7,
            name, title)


    @commands.command(aliases=['r1999'])
    async def reverse1999(self, ctx):
        await ctx.defer()
        url = f"https://reverse1999.fandom.com/api.php"

        characters = await self.mediawiki_category(url,
            "Category:Garments")

        valid_article = False
        while not valid_article:
            article = choice(characters)["title"]
            
            page = await self.mediawiki_parse(url, article)
            
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
        if "Default" in title:
            title = ""

        img = skin.xpath(".//figure/a/@href")[0]
        await self.bot.get_channel(DEBUG_CHANNEL).send(f"r1999 {img}")

        file = await self.url_to_file(img)

        await self.post(ctx, file, "Reverse: 1999", 0x53443c, name, title,
            "reverse 1999")


    #@commands.command(aliases=['atelier'])
    async def atelieresleriana(self, ctx):
        await ctx.defer()

        # JSON Updated March 29, 2025
        with open("ext/data/gacha/atelier.json") as f:
            char = choice(json.load(f))

        img = ("https://barrelwisdom.com/media/games/resleri/characters/"
            f"full/{char['slug']}.webp")
        game_name = ("Atelier Resleriana: Forgotten Alchemy "
        "and the Polar Night Liberator")

        await self.post(ctx, img, game_name, 0x845b51, char["name"],
            char["title"], "atelier reseleriana")


    @commands.command()
    async def sinoalice(self, ctx):
        await ctx.defer()

        file, char_path = await self.get_github("orbicube/sinoalice",
            "1b0c543065d69fa45d4cebcd539ff900e2517020")

        name, title = char_path[:-4].split("#")

        await self.post(ctx, file, "SINoALICE", 0xfafafa, name, title)


    @commands.command(aliases=['touhou'])
    async def touhoulostword(self, ctx):
        await ctx.defer()
        base_url = "https://lostwordchronicle.com"

        characters = self.check_cache("touhou")
        if not characters:
            r = await self.bot.http_client.get(
                f"{base_url}/characters/ajax")
            results = r.json()["data"]

            characters = []
            for r in results:
                char = {
                    "name": f"{r['name']} ({r['universe']})",
                    "id": r['character']
                }
                characters.append(char)

            self.write_cache("touhou", characters)

        char = choice(characters)

        r = await self.bot.http_client.get(
            f"{base_url}/lorepedia/characters/{char['id']}")
        page = html.fromstring(r.text)

        costumes = page.xpath("//div[@id='character-costume']/div/img/@src")
        picked_costume = randint(0, len(costumes)-1)

        costume_title = page.xpath(("//div[@id='costume-information']"
            f"/p[@id='costume-title-{picked_costume}']/text()"))[0]

        img_url = f"{base_url}{costumes[picked_costume]}"

        await self.post(ctx, img_url, "Touhou LostWord", 0xef5a68,
            char["name"], costume_title)


    @commands.command()
    async def worldflipper(self, ctx):
        await ctx.defer()

        file, char_path = await self.get_github("orbicube/worldflip",
            "da2abbedf7207fa36707017fe5ad841edd5556ca")

        name, title = char_path[:-4].split("#")

        if "_" in title:
            title = title.replace("_", ":")
        if "!" in title:
            title = title[:-1]

        await self.post(ctx, file, "World Flipper", 0xb2d8ee, name, title)


    @commands.command(aliases=['kof'])
    async def kofallstar(self, ctx):
        await ctx.defer()

        file, char_path = await self.get_github("orbicube/kofchars",
            "dad49f27c6cc4a766cfbb96c077bac925c146ee1")

        name, game = char_path[:-4].split("#")

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

        await self.post(ctx, file, "The King of Fighters ALLSTAR", 0xfc9a4c,
            name, game, "kof")


    @commands.command(aliases=['404gamereset', '404'])
    async def errorgamereset(self, ctx):
        await ctx.defer()
        
        file, char_path = await self.get_github("orbicube/404chars",
            "58b9eb8f0c5e4ea34ec74b103d458458e788482e")

        try:
            name, type = char_path[:-4].split("#")
        except:
            name = char_path[:-4]
            type = ""

        await self.post(ctx, file, "404 GAME RE:SET", 0x7f7f80,
            name, type, "404 game reset")


    @commands.command()
    async def bravefrontier(self, ctx):
        await ctx.defer()
        url = "https://bravefrontierglobal.fandom.com/api.php"

        with open("ext/data/gacha/bfunits.txt", encoding="utf-8") as f:
            title = choice([line.rstrip() for line in f])

        page = await self.mediawiki_parse(url, title)

        img = page.xpath(("//div[@class='tabber wds-tabber']/div/div/center"
            "/span/a/@href"))[0]

        file = await self.url_to_file(img)

        await self.post(ctx, file, "Brave Frontier", 0xbfb135, title)


    @commands.command()
    async def langrisser(self, ctx):
        await ctx.defer()
        
        url = "https://wiki.biligame.com/langrisser/api.php"

        characters = self.check_cache("langrisser")
        if not characters:
            
            characters = await self.mediawiki_category(url,
                category="分类:英雄")

            self.write_cache("langrisser", characters)              

        char = choice(characters)["title"]

        page = await self.mediawiki_parse(url, char)        

        name = page.xpath("//div[@class='HeroInfo_Name_EN']/text()")[0]
        skin = choice(
            page.xpath("//div[@class='HeroInfo_Skin_Img']/img/@src"))
        skin = skin.rsplit("/", 1)[0].replace("/thumb", "")

        file = await self.url_to_file(skin)

        await self.post(ctx, file, "Langrisser", 0xde181d, name)


    @commands.command()
    async def cookierun(self, ctx):
        await ctx.defer()

        url = "https://cookierunkingdom.fandom.com/api.php"
        
        chars = await self.mediawiki_category(url,
            "Category:Playable_Cookies")
        char = choice(chars)["title"]

        page = await self.mediawiki_parse(url, char)

        img = page.xpath(("//div[@class='pi-image-collection wds-tabber']"
            "/div/figure/a/@href"))[0]

        file = await self.url_to_file(img)

        await self.post(ctx, file, "Cookie Run: Kingdom", 0xc0ab76,
            char.replace(' Cookie', ''), game_short="cookie run")

    @commands.command(aliases=['mmxd'])
    async def megamanxdive(self, ctx):
        await ctx.defer()

        url = "https://rockman-x-dive.fandom.com/api.php"
        
        chars = await self.mediawiki_category(url,
            "Category:Characters/Playable")
        char = choice(chars)["title"]

        page = await self.mediawiki_parse(url, char)
        img = page.xpath("//figure[@class='pi-item pi-image']/a/@href")[0]

        file = await self.url_to_file(img)

        await self.post(ctx, file, "Mega Man X DiVE", 0x1a7acb, char)


    @commands.command(aliases=['saga'])
    async def romancingsaga(self, ctx):
        await ctx.defer()

        with open("ext/data/gacha/romancingsaga.json") as f:
            char = choice(json.load(f))

        img = ("https://rsrs.xyz/assets/gl/texture/style/"
            "{char['id']}/style_{char['id']}.png")

        await self.post(ctx, img, "Romancing SaGa re;univerSe", 0x8f0000,
            char["name"], char["title"])


    @commands.command(aliases=['ffbe', 'exvius'])
    async def braveexvius(self, ctx):
        await ctx.defer()

        url = "https://exvius.fandom.com/api.php"
        
        chars = await self.mediawiki_category(url,
            "Category:Units")
        char = choice(chars)["title"]
        await self.bot.get_channel(DEBUG_CHANNEL).send(f"ffbe {char}")

        page = await self.mediawiki_parse(url, char)
        
        variant = choice(page.xpath("//table[@class='wikitable unit ibox']"))
        name = variant.xpath(".//tr[1]/th/text()")[0]
        img = variant.xpath(".//tr[2]/td/span/span/img/@src")[0]

        file = await self.url_to_file(img, resize=3.0)

        await self.post(ctx, file, "Final Fantasy Brave Exvius", 0x9adafe,
            name, "brave exvius")


    @commands.command(aliases=['bbdw'])
    async def blazblue(self, ctx):
        await ctx.defer()

        with open("ext/data/gacha/bbdw.json", encoding="utf-8") as f:
            char = choice(json.load(f))

        file = await self.url_to_file(choice(char["art"]))

        await self.post(ctx, file, "BlazBlue Alternative: Dark War", 0x4986c1,
            char["name"], char["title"], "blazblue dark war")


    @commands.command()
    async def umamusume(self, ctx):
        await ctx.defer()

        url = "https://umapyoi.net/api/v1/character"
        r = await self.bot.http_client.get(f"{url}/list")
        char = choice([c for c in r.json()
            if c["category_label_en"] != "Related parties"])

        r = await self.bot.http_client.get(f"{url}/images/{char['id']}")
        outfit = choice([o for o in r.json() if o["label_en"] == "Racewear"])

        file = await self.url_to_file(outfit["images"][0]["image"])

        await self.post(ctx, file, "Umamusume: Pretty Derby", 0xd88da4,
            char["name_en"], game_short = "umamusume")


    @commands.command()
    async def afkarena(self, ctx):
        await ctx.defer()

        url = "https://afkarena.fandom.com/api.php"

        bad_pages = [85, 341, 966, 1126, 1971, 3278, 3284, 3297, 5566, 5568]
        char_list = await self.mediawiki_category(url,
            "Category:Heroes", bad_pages, vignette=True)
        char = choice(char_list)

        file = await self.get_imageinfo(url, char['pageimage'])

        title = ""
        if " - " in char["title"]:
            name, title = char["title"].split(" - ")
        else:
            name = char["title"]

        await self.post(ctx, file, "AFK Arena", 0xd5a749, name, title)


    @commands.command(aliases=['octopath', 'cotc'])
    async def octopathtraveler(self, ctx):
        await ctx.defer()

        file, char_path = await self.get_github("orbicube/octopath",
            "45fbdaeba65431cf1d82266138c662d9ebc2221b")

        name = char_path[:-4]
        title = ""
        if " EX" in name:
            title = "EX"
            name = name[:-3]

        await self.post(ctx, file,
            "Octopath Traveler: Champions of the Continent",
            0xcabf9e, name, title, "octopath")

    @commands.command()
    async def bravelydefault(self, ctx):
        await ctx.defer()

        file, char_path = await self.get_github("orbicube/bravelydefault",
            "5352a20a1f42bd3e80573201163ea212b65f8ebc")

        name, title = char_path[:-4].split("#")

        try:
            title_map = {"1star": "★", "3star": "★★★", "5star": "★★★★★"}
            name += f" {title_map[title]}"
            title = ""
        except:
            pass

        await self.post(ctx, file, "Bravely Default: Brilliant Lights",
            0xb0c0b3, name, title, "bravely default")


    @commands.command()
    async def echoesofmana(self, ctx):
        await ctx.defer()

        file, char_path = await self.get_github("orbicube/echoesofmana",
            "2a0b478efb52e81d9a6c490a448430e94676869c")

        name, title = char_path[:-4].split("#")
        if title == "Base":
            title = ""

        await self.post(ctx, file, "Echoes of Mana", 0xa6bbad, name, title)


    @commands.command(aliases=['soa'])
    async def starocean(self, ctx):
        await ctx.defer()
        url = "https://starocean.fandom.com/api.php"

        with open("ext/data/gacha/starocean.json") as f:
            char = choice(json.load(f))
        variant = choice(char["variants"])

        file = await self.get_imageinfo(url, variant["img"])

        await self.post(ctx, file, "Star Ocean: Anamnesis",
            0x127799, char["name"], variant["title"], "star ocean")


    @commands.command()
    async def nikke(self, ctx):
        await ctx.defer()
        url = ("https://nikke-goddess-of-victory-international"
            ".fandom.com/api.php")
        
        chars = await self.mediawiki_category(url,
            "Category:Playable_characters")
        char = choice(characters)["title"]
        await self.bot.get_channel(DEBUG_CHANNEL).send(f"nikke {char}")

        page = await self.mediawiki_parse(url, char)

        titles = page.xpath(("//div[@class='pi-image-collection wds-tabber']"
            "/div/ul/li/span/text()"))
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

        img = page.xpath(
            "//figure[@class='pi-item pi-image']/a/@href")[selected].replace(
            'MI.png/', 'FB.png/')
        file = await self.url_to_file(img)

        await self.post(ctx, file, "Goddess of Victory: Nikke",
            0xb4b3bb, char, title, "nikke")


    @commands.command(aliases=['msa'])
    async def metalslug(self, ctx):
  
        file, char_path = await self.get_github("orbicube/msa",
            "3dca6069518ed7ba82bc9e85e2547063689ba155")

        try:
            name, title = char_path[:-4].split("#")
        except:
            name = char_path[:-4]
            title = ""

        await self.post(ctx, file, "Metal Slug Attack", 0xde8a39,
            name, title, "metal slug")


    @commands.command()
    async def anothereden(self, ctx):
        await ctx.defer()

        url = "https://anothereden.wiki/api.php"
            
        page = await self.mediawiki_parse(url, "Collection_Tracker")

        char = choice(page.xpath(
            "//div[@class='tracker-item tracker-character']"))
        name = char.xpath("./@data-name")[0]
        if " (" in name:
            name, title = name.split(" (")
            title = title[:-1]
        else:
            title = ""
        img = char.xpath(".//a/img/@src")[0][13:-9].replace("command", "base")
        
        file = await self.get_imageinfo(url, img)

        await self.post(ctx, file, "Another Eden", 0x5e76af, name, title)


    @commands.command()
    async def terrabattle(self, ctx):
        await ctx.defer()
        url = "https://terrabattle.fandom.com/api.php"

        with open("ext/data/gacha/terrabattle.json") as f:
            chars = json.load(f)
            char = choice(list(chars.keys()))
        variant = choice(chars[char])

        game_name = "Terra Battle"
        if "Guardian_" in variant['img']:
            url = url.replace("e.f", "e2.f")
            game_name = "Terra Battle 2"

        file = await self.get_imageinfo(url, variant['img'])

        await self.post(ctx, file, game_name, 0x648ba5, char, variant["title"])


    @commands.command(aliases=['ptn'])
    async def pathtonowhere(self, ctx):
        await ctx.defer()
        base_url = "https://pathtonowhere.wiki.gg"
        url = f"{base_url}/api.php"

        characters = self.check_cache("ptn")
        if not characters:
            
            characters = await self.mediawiki_category(url,
                "Category:Sinner Attires")

            self.write_cache("ptn", characters)            

        char = choice(characters)["title"]
        char_name = char.rsplit("/", 1)[0]
        await self.bot.get_channel(DEBUG_CHANNEL).send(f"ptn {char}")

        page = await self.mediawiki_parse(url, char)

        default_imgs = page.xpath("//tr/td/a[@class='image']")
        skin_imgs = page.xpath("//aside/figure[@data-source='Image']/a")
        all_imgs = default_imgs + skin_imgs
        if not all_imgs:
            await self.bot.get_channel(DEBUG_CHANNEL).send(f"no imgs")
            await self.pathtonowhere(ctx, reason)
        else:
            selected_img = choice(all_imgs)
            img = selected_img.xpath("./@href")[0].rsplit("/File:", 1)[1]
            
            file = await self.url_to_file(f"{base_url}/images/{img}")

            if "Skin" not in img:
                title = ""
            else:
                if "Skin1" in img:
                    title = "Phase Up"
                else:
                    title = selected_img.xpath(
                        "../preceding-sibling::h2/text()")[0]

            await self.post(ctx, file, "Path to Nowhere",
                0xa21f23, char_name, title)


    @commands.command(aliases=['p5x'])
    async def persona5x(self, ctx):
        await ctx.defer()

        url = "https://lufel.net/"

        characters = self.check_cache("p5x")
        if not characters:
            r = await self.bot.http_client.get(
                f"{url}data/kr/characters/characters.js")
            temp_dict = r.text.split("characterData = ")[1].split(
                "},", 1)[1][:-3]
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

            self.write_cache("p5x", characters)

        char = choice(characters)

        file = await self.url_to_file(
            f"{url}assets/img/character-detail/{char['key']}.webp",
            filename=f"{char['name']}.webp")

        await self.post(ctx, file, "Persona 5: The Phantom X",
            0xf30002, char["name"], char["title"], game_short="persona 5 x")


    @commands.command(aliases=['genshin'])
    async def genshinimpact(self, ctx):
        await ctx.defer()

        url = "https://genshin-impact.fandom.com/api.php"

        page = await self.mediawiki_parse(url, "Wish/Gallery")

        char = choice(page.xpath(("//div[@id='gallery-3']"
            "/div[@class='wikia-gallery-item']")))

        char_name = char.xpath(
            ".//div[@class='lightbox-caption']/a/text()")[0]
        img = char.xpath(
            ".//div[@class='thumb']/div/a/img/@data-image-key")[0]

        file = await self.get_imageinfo(url, img)

        await self.post(ctx, file, "Genshin Impact", 0xa4ec93, char_name)


    @commands.command(aliases=['hsr'])
    async def honkaistarrail(self, ctx):
        await ctx.defer()
        url = "https://honkai-star-rail.fandom.com/api.php"

        char_list = await self.mediawiki_category(url,
            "Category:Playable_Characters", vignette=True)

        char = choice(char_list)

        file = await self.get_imageinfo(url, char['pageimage'])

        await self.post(ctx, file, "Honkai Star Rail", 0x648fb8, char["title"])


    @commands.command(aliases=['zzz'])
    async def zenlesszonezero(self, ctx):
        await ctx.defer()
        url = "https://zenless-zone-zero.fandom.com/api.php"
        
        char_list = await self.mediawiki_category(url,
            "Category:Playable_Agents", vignette=True)

        char = choice(char_list)

        file = await self.get_imageinfo(url, char['pageimage'])

        await self.post(ctx, file, "Honkai Star Rail", 0xb9d600, char["title"])


    @commands.command()
    async def dislyte(self, ctx):
        await ctx.defer()
        url = "https://dislyte.fandom.com/api.php"

        char_list = await self.mediawiki_category(url,
            "Category:Esper_galleries")

        char = choice(char_list)["title"]
        char_name, char_deity = char.split(")/")[0].split(" (")

        page = await self.mediawiki_parse(url, char)

        skin = choice(page.xpath(
            "//div/table[@class='dis-atable']"))
        skin_name = skin.xpath("//tbody/tr[1]/th/text()")[0]
        if "Default" in skin_name:
            skin_name = ""

        img = skin.xpath(
            "//tbody/tr[2]/td/figure/a/@href")[0]
        file = await self.url_to_file(img)

        await self.post(ctx, file, "Dislyte", 0xadebe3,
            char_name, skin_name, author=char_deity)


    @commands.command(aliases=['ff7ec'])
    async def evercrisis(self, ctx):
        await ctx.defer()
        url = "https://finalfantasy.fandom.com/api.php"

        page = await self.mediawiki_parse(url,
            "Final Fantasy VII Ever Crisis gear")

        skin = choice(page.xpath("//img[not(@alt='Userbox ff7-barret')]"))
        char_name = skin.xpath(
            "./ancestor::table/preceding::h3[1]/span/a/text()")[0]
        char_title = skin.xpath("./ancestor::tr/td[2]/span/text()")[0]

        img = skin.xpath("../@href")[0]
        file = await self.url_to_file(img)

        await self.post(ctx, file, "Final Fantasy VII Ever Crisis", 0xe9d7b5,
            char_name, char_title, "ever crisis")


    @commands.command()
    async def foodfantasy(self, ctx):
        await ctx.defer()
        url = "https://food-fantasy.fandom.com/api.php"

        bad_pages = [4585, 1752, 29713, 143]
        char_list = await self.mediawiki_category(url,
            "Category:Food_Souls")

        char = choice(char_list)["title"]

        page = await self.mediawiki_parse(url, char)

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

        img = sections[selected_skin].xpath(
            "./div[1]/div/span/a/@href")[0]

        file = await self.url_to_file(img)

        await self.post(ctx, file, "Food Fantasy", 0xf6be41, char, skin_name)


    @commands.command()
    async def resonancesolstice(self, ctx):
        await ctx.defer()

        url = "https://wiki.biligame.com/resonance/api.php"

        characters = self.check_cache("resosol")
        if (datetime.utcnow() - last_up) / timedelta(weeks=1) > 1:
            
            characters = await self.mediawiki_category(url,
                category="分类:乘员")

            self.write_cache("resosol", characters)

        char = choice(characters)["title"]

        page = await self.mediawiki_parse(url, char)
        
        info = page.xpath("//div[@class='resp-tab-content'][1]/div")[0]
        char_name = info.xpath(
            "./div[@class='rh-info']/div[2]/div[2]/text()")[0]
        img = info.xpath("./div[@class='rh-portrait']/img/@src")[0]

        file = await self.url_to_file(img)

        await self.post(ctx, file, "Resonance Solstice", 0x3f4149, char_name)


    @commands.command(aliases=['potk'])
    async def phantomofthekill(self, ctx):
        with open("./ext/data/gacha/potk.json") as f:
            chars = json.load(f)

        img = choice([*chars])
        char_name = chars[img]

        await self.post(ctx, img, "Phantom of the Kill", 0xaf989a, char_name)


    @commands.command(aliases=['wuwa'])
    async def wutheringwaves(self, ctx):
        await ctx.defer()
        url = "https://wutheringwaves.fandom.com/api.php"

        bad_pages = [709]
        char_list = await self.mediawiki_category(url,
            "Category:Outfits", bad_pages)

        char = choice(char_list)["title"]

        page = await self.mediawiki_parse(url, char)

        info = page.xpath("//aside")[0]
        outfit = info.xpath("./h2/text()")[0]
        char_name = info.xpath(
            "./div[@data-source='character']/div/a/text()")[0]

        img = info.xpath("./figure/a/@href")[0]
        file = await self.url_to_file(img)

        await self.post(ctx, file, "Wuthering Waves", 0x4a6da1,
            char_name, outfit)


    @commands.command()
    async def alchemistcode(self, ctx):
        await ctx.defer()
        url = "https://thealchemistcode.fandom.com/api.php"

        char_list = await self.mediawiki_category(url,
            "Category:Units")

        char = choice(char_list)["title"]

        page = await self.mediawiki_parse(url, char)

        char_name = page.xpath("//aside/h2/text()")[0]
        img = page.xpath("//figure/a/@href")[0].replace(
            "Images2%2C", "Images%2C")

        file = await self.url_to_file(img)

        await self.post(ctx, file, "Alchemist Code", 0xa26a42, char_name)


    @commands.command()
    async def ashechoes(self, ctx):
        await ctx.defer()
        base_url = "https://ashechoes.wiki.gg"
        url = f"{base_url}/api.php"

        char_list = await self.mediawiki_category(url,
            "Category:Echomancer")
        char = choice(char_list)["title"]

        page = await self.mediawiki_parse(url, char)
 
        char_name = page.xpath(
            "//div/div[1]/table/tbody/tr/td/span/text()")[0].split(" (")[0]
        img = choice(page.xpath("//div/div[2]//a/img/../@href")).rsplit(
            "/File:", 1)[1]
        img_url = f"{base_url}/images/{img}"

        skin_type = img.rsplit("-", 1)[1]
        if "Base" in skin_type:
            skin_type = ""
        elif "Senlo" in skin_type:
            skin_type = "Senlo Mirage"

        file = await self.url_to_file(img_url)

        await self.post(ctx, file, "Ash Echoes", 0x43c2ff,
            char_name, skin_type)


    @commands.command()
    async def endfield(self, ctx):
        await ctx.defer()
        base_url = "https://endfield.wiki.gg"
        url = f"{base_url}/api.php"

        page = await self.mediawiki_parse(url, "Operator/List")

        char = choice(page.xpath(
            "//div[@class='ranger-list']/div/div[2]/a/@title"))

        page = await self.mediawiki_parse(url, char)

        char_base = choice(page.xpath("//img[@class='character-image']"))

        try:
            char_title = char_base.xpath("./../../@data-druid-tab-key")[0]
        except:
            char_title = ""

        img = char_base.xpath("./../@href")[0].rsplit("/File:", 1)[1]
        img_url = f"{base_url}/images/{img}"
        file = await self.url_to_file(img_url)

        await self.post(ctx, file, "Arknights: Endfield", 0xfff100,
            char, char_title, "endfield") 


    @commands.command(aliases=['pgr'])
    async def punishinggrayraven(self, ctx):
        await ctx.defer()
        base_url = "https://grayravens.com"
        url = f"{base_url}/w/api.php"

        page = await self.mediawiki_parse(url, "Characters")

        char_name = choice(page.xpath(
            "//table/tbody/tr/td[1]/small/a/text()"))

        page = await self.mediawiki_parse(url, f"{char_name}/Gallery")

        temp_skins = page.xpath("//section/article/figure[@typeof='mw:File']")
        skins = []
        for skin in temp_skins:
            if not "Generic_-_" in skin.xpath("./../@id")[0]:
                skins.append(skin)

        skin = choice(skins)
        if "Generic" in skin.xpath("./../@id")[0]:
            skin = choice(page.xpath((
                "//div[@class='column-left']/center/div/"
                "section/article/figure[@typeof='mw:File']")))

        skin_name = skin.xpath("./../@id")[0][7:].replace("_", " ")
        if "Generic" in skin_name:
            if skin_name == "Generic":
                skin_name = ""
            else:
                skin_name = skin_name.split(" - ")[1]

        img = skin.xpath("./a/@href")[0].rsplit("/File:", 1)[1]
        file = await self.get_imageinfo(url, img)

        await self.post(ctx, file, "Punishing Gray Raven", 0x870328,
            char_name, skin_name)


    @commands.command()
    async def etheriarestart(self, ctx):
        await ctx.defer()
        url = "https://etheriarestart.fandom.com/api.php"

        char_list = await self.mediawiki_category(url,
            "Category:Animus", vignette=True)

        char = choice(char_list)

        file = await self.get_imageinfo(url, char["pageimage"])

        await self.post(ctx, file, "Etheria: Restart", 0xdc1a54, 
            char["title"], game_short="etheria restart")


    @commands.command()
    async def mecharashi(self, ctx):
        await ctx.defer()
        # https://ma-us-community.tentree-games.com/?lang=en
        url = ("https://usma-activity.tentree-games.com/"
            "common/infodata/mQuery.do")
        params = {
            "appkey": 1722917077707,
            "target": "pilot_data",
            "type": "list",
            "lang": "en"
        }

        r = await self.bot.http_client.get(url, params=params)
        chars = r.json()["data"]["data"]

        char = choice(chars)

        img = ("https://media.tentree-games.com/media/pictures/community/"
            f"img/gl/gameInfo/character/{char['AvatarHeroIcon']}.png")
        file = await self.url_to_file(img)

        await self.post(ctx, file, "Mecharashi", 0xeddadb, char["RealName"])


    #@commands.command()
    async def alchemystars(self, ctx):
        await ctx.defer()
        url = "https://alchemystars.fandom.com/api.php"


    @commands.command()
    async def aethergazer(self, ctx):
        await ctx.defer()
        url = "https://mimir.cat"

        characters = self.check_cache("aethergazer")
        if not characters:
            r = await self.bot.http_client.get(url)
            page = html.fromstring(r.text)

            characters = page.xpath(
                "//div[@class='character-grid']/a/@href")

            self.write_cache("aethergazer", characters)

        char = choice(characters)

        r = await self.bot.http_client.get((f"{url}/_next/data/mimir"
            f"{char}profile.json"))
        char_data = r.json()["pageProps"]["profileData"]

        char_name = char_data["record"]["name"]["en"]
        char_title = char_data["record"]["title"]["en"]

        skin = choice(char_data["skins"])
        skin_name = skin["name"]["en"]
        if char_title in skin_name:
            skin_name = ""

        file = await self.url_to_file(("https://box.mimir.cat/images/skin/"
            f"{char_data['record']['game_id']}/{skin['id']}.png"))

        await self.post(ctx, file, "Aether Gazer", 0xf5bdc7,
            char_name, skin_name, author=char_title)


    @commands.command()
    async def convallaria(self, ctx):
        await ctx.defer()

        file, char_path = await self.get_github("orbicube/convallaria",
            "577e43145d9e4a8a0a408c9b6c7c7483a1e1d3da")

        try:
            name, title = char_path[:-4].split("#")
            if title.endswith("!"):
                title = title[:-1]
        except:
            name = char_path[:-4]
            title = ""

        await self.post(ctx, file, "Sword of Convallaria", 0x8cc2b3,
            name, title, game_short="convallaria")

async def setup(bot):
    await bot.add_cog(Gacha(bot))