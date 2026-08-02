import discord
from discord import app_commands
from discord.ext import commands

from typing import Optional
from random import choice, choices, randint, sample

from lxml import html
from PIL import Image
from io import BytesIO
from base64 import b64decode
from urllib.parse import quote
from datetime import datetime, timedelta

import json

from credentials import DEBUG_CHANNEL, GOOGLE_KEY

class Card(commands.Cog,
    command_attrs={"cooldown": commands.CooldownMapping.from_cooldown(
        2, 15, commands.BucketType.user)}):

    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command()
    @app_commands.describe(game="TCG you want to pull a card from")
    async def card(self, ctx, game: Optional[str] = None, reason: Optional[str] = None):
        
        commands = self.get_commands()
        selected_comm = next((
            c for c in commands if c.name == game or game in c.aliases), None)

        if ctx.interaction:
            ctx.interaction.extras = {"random": False}

            if reason:
                ctx.interaction.extras["reason"] = reason

        if not selected_comm:
            selected_comm = choice(commands)

            await self.bot.get_channel(DEBUG_CHANNEL).send(selected_comm.name)

            if ctx.interaction:
                ctx.interaction.extras["random"] = True

        await selected_comm.__call__(ctx)


    @card.autocomplete('game')
    async def card_autocomplete(self, 
        interaction: discord.Interaction,
        current: str,) -> list[app_commands.Choice[str]]:

        games = [c.name for c in self.get_commands()
            if not "playingcard" in c.name and not c.name == "card"]
        completes = [app_commands.Choice(name=game, value=game)
            for game in games if current.lower() in game.lower()]

        if not current:
            completes = sample(completes, len(completes))

        return completes[:25] 


    async def tcgplayer_rand(self, game: str):
        url = "https://mp-search-api.tcgplayer.com/v1/search/request"
        data = {
            "filters": {
                "term" : {
                    "productLineName": [game],
                    "productTypeName": ["Cards"]
                }
            },
            "size": 1,
            "sort": {
                "field": "product-sorting-name",
                "order": "asc"
            }
        }
        r = await self.bot.http_client.post(url, json=data)
        card_count = r.json()["results"][0]["totalResults"]
        data["from"] = randint(0, int(card_count))

        print(data["from"])

        r = await self.bot.http_client.post(url, json=data)
        card = choice(r.json()["results"][0]["results"])

        card_id = int(card["productId"])
        card_img = f"https://tcgplayer-cdn.tcgplayer.com/product/{card_id}_in_1000x1000.jpg"

        return card_img


    async def netdeck_rand(self, game: str):
        url = f"https://api.netdeck.gg/api/cards/{game}"
        params = {
            "limit": 1
        }
        r = await self.bot.http_client.get(url, params=params)

        card_count = r.json()["total"]
        params["offset"] = randint(0, card_count-1)

        r = await self.bot.http_client.get(url, params=params)
        card = r.json()["items"][0]

        return card


    async def carde_rand(self, game: int):
        url = "https://api.admin.carde.io/api/v2/deckbuilder/cards/search-with-filters/"
        js_data = {
            "game_id": game,
            "limit": 1
        }

        r = await self.bot.http_client.post(url, json=js_data)
        card_count = r.json()["total"]
        js_data["offset"] = randint(0, card_count-1)

        r = await self.bot.http_client.post(url, json=js_data)
        card = r.json()["cards"][0]

        return card


    async def post(self, ctx: commands.Context, img: discord.File|str, game_name: str):
        msg = ""
        try:
            reason = ctx.interaction.extras["reason"]
            if ctx.interaction.extras["random"]:
                game_name = "card"
            msg = f"{game_name} {reason}:"
        except:
            pass

        files = []
        if isinstance(img, str):
            msg += f"[⠀]({img})"
        else:
            files = [img]

        await ctx.send(msg, files=files)


    def check_cache(self, filename: str):
        try:
            with open(f"ext/data/card/{filename}.json",
                encoding="utf-8") as f:
                j = json.load(f)
        except:
            return []

        last_up = datetime.utcfromtimestamp(j["updated"])
        if (datetime.utcnow() - last_up) / timedelta(weeks=1) > 3:
            return None
        else:
            return j["cards"]


    def write_cache(self, filename: str,
        cards: list):

        data = {
            "updated": int(datetime.utcnow().timestamp()),
            "cards": cards
        }

        with open(f"ext/data/card/{filename}.json", "w",
            encoding="utf-8") as f:
            json.dump(data, f)


    @commands.command(aliases=['poke'])
    async def pokemon(self, ctx):
        await ctx.defer()

        url = "https://pkmncards.com/?random"
        r = await self.bot.http_client.get(url, follow_redirects=True)

        # Scrape image from page metadata
        page = html.fromstring(r.text)
        image_url = page.xpath("//meta[@property='og:image']/@content")[0]
        image_url = image_url.split('?')[0]

        await self.post(ctx, image_url, "pokemon")


    @commands.command(aliases=['ygo', 'yugi'])
    async def yugioh(self, ctx):
        await ctx.defer()

        url = "https://db.ygoprodeck.com/api/v7/cardinfo.php"
        params = {
            "num": 1, "offset": 0, "sort": "random", "cachebust": 1
        }
        r = await self.bot.http_client.get(url, params=params)
        card = r.json()["data"][0]

        await self.post(ctx, card['card_images'][0]['image_url'], "yugioh")


    @commands.command()
    async def digimon(self, ctx):
        await ctx.defer()

        # Git tree for cardlist, updated 2025/07/10
        tree = "00bef43e2222b3635dd69da0271a840c90a7986c"
        url = ("https://api.github.com/repos/TakaOtaku/"
            f"Digimon-Cards/git/trees/{tree}")
        r = await self.bot.http_client.get(url, timeout=10.0)
        cards = r.json()["tree"]

        filters = ["-J.", "-j", "-Sample"]
        cards = [card for card in cards if not any(f in card["path"] for f in filters)]
        card = choice(cards)

        r = await self.bot.http_client.get(card["url"])
        img = b64decode(r.json()["content"])
        file = discord.File(
            fp=BytesIO(img),
            filename=card["path"])

        await self.post(ctx, file, "digimon")


    @commands.command(aliases=['magic'])
    async def mtg(self, ctx):
        await ctx.defer()

        url = "https://api.scryfall.com/cards/random"
        r = await self.bot.http_client.get(url, timeout=15)
        card = r.json()

        # If it doesn't have an image then try again
        card_status = card['image_status']
        if card_status == 'missing' or card_status == 'placeholder':
            await self.mtg(ctx)
        else:
            # If card has two sides, pick one side
            if not "image_uris" in card and "card_faces" in card:
                card['image_uris'] = card['card_faces'][randint(0,1)]['image_uris']
            
            await self.post(ctx, card['image_uris']['png'], "mtg")


    @commands.command(aliases=['fab'])
    async def fleshandblood(self, ctx):
        await ctx.defer()

        url = "https://cards.fabtcg.com/api/search/v1/cards/"
        params = {
            "limit": 1
        }
        r = await self.bot.http_client.get(url, params=params)
        card_count = r.json()["count"]

        params["offset"] = randint(0, int(card_count)-1)
        r = await self.bot.http_client.get(url, params=params)
        card = r.json()["results"][0]

        await self.post(ctx, card["image"]["large"], "flesh and blood")


    @commands.command()
    async def gateruler(self, ctx):
        await ctx.defer()

        # Get max page number
        url = "https://www.gateruler-official.com/card_search"
        r = await self.bot.http_client.get(url)
        page = html.fromstring(r.text)

        max_pages = page.xpath("//ul[@class='pagination']/li/a/text()")[-2]

        # Pick random page
        params = { "page": randint(1, int(max_pages)) }
        r = await self.bot.http_client.get(url, params=params)
        page = html.fromstring(r.text)

        # Get random card       
        cards = page.xpath("//li[@class='com_btm']/a/img/@src")
        card_url = choice(cards)

        r = await self.bot.http_client.get(card_url)

        # Crop borders of card
        card_img = Image.open(BytesIO(r.content))
        card_img = card_img.crop(card_img.getbbox())

        # Send to Discord
        with BytesIO() as img_binary:
            card_img.save(img_binary, 'PNG')
            img_binary.seek(0)
            file = discord.File(
                fp=img_binary,
                filename=card_url.rsplit('/', 1)[1])

        await self.post(ctx, file, "gate ruler")
  

    @commands.command(aliases=["cfv", "vanguard", "cardfight"])
    async def cardfightvanguard(self, ctx):
        await ctx.defer()

        url = "https://www.tcgstacked.com/api/v2/search/cards"
        params = {
            "tcg": "vanguard",
            "page": 1,
            "hitsPerPage": 1
        }
        r = await self.bot.http_client.get(url, params=params)

        card_count = r.json()["pagination"]["totalHits"]
        params["page"] = randint(1, card_count)

        r = await self.bot.http_client.get(url, params=params)
        card = r.json()["data"][0]["images"]["large"]

        await self.post(ctx, card, "cardfight vanguard")


    @commands.command()
    async def grandarchive(self, ctx):
        await ctx.defer()

        r = await self.bot.http_client.get(
            "https://api.gatcg.com/cards/random?amount=1")
        card = r.json()[0]
        card_slug = choice(card["editions"])["slug"]
        card_url = f"https://ga-index-public.s3.us-west-2.amazonaws.com/cards/{card_slug}.jpg"
        
        await self.post(ctx, card_url, "grand archive")


    @commands.command()
    async def nostalgix(self, ctx):
        await ctx.defer()

        url = "https://play-api.carde.io/v1/cards/63bc844c3e8d2f34e312bc77"

        r = await self.bot.http_client.get(url)
        max_pages = r.json()["pagination"]["totalPages"]

        params = { "page": randint(1, int(max_pages)) }

        r = await self.bot.http_client.get(url, params=params)
        cards = r.json()["data"]
        card_img = choice(cards)["imageUrl"]

        await self.post(ctx, card_url, "nostalgix")


    @commands.command()
    async def lorcana(self, ctx):
        await ctx.defer()

        r = await self.bot.http_client.get("https://api.lorcana-api.com/bulk/cards")
        cards = r.json()
        card_img = choice(cards)["Image"]

        await self.post(ctx, card_img, "lorcana")


    @commands.command()
    async def redemption(self, ctx):
        await ctx.defer()

        # Git tree for cardlist, updated 2025/06/24
        tree = "bb007936c69375fdb5631becceafa62e4975e886"
        url = ("https://api.github.com/repos/MattJBrinkman/"
            f"RedemptionLackeyCCG/git/trees/{tree}")

        r = await self.bot.http_client.get(url)
        cards = r.json()["tree"]

        cards = [card for card in cards if ".jpg" in card["path"]]
        card = choice(cards)

        r = await self.bot.http_client.get(card["url"])
        img = b64decode(r.json()["content"])
        file = discord.File(
            fp=BytesIO(img),
            filename=card["path"])

        await self.post(ctx, file, "redemption")


    @commands.command()
    async def vampire(self, ctx):
        await ctx.defer()

        # Git tree for cardlist, updated 2024/09/22
        tree = "8661079bd3f85ce9bf899c23e945d8fd0f2a1334"
        url = ("https://api.github.com/repos/lionel-panhaleux/"
            f"krcg-static/git/trees/{tree}")

        r = await self.bot.http_client.get(url)
        cards = r.json()["tree"]

        # Filter out subdirectories
        cards = [card for card in cards if card["type"] == "blob"]
        # Remove entries with size < 100 as they're symlinks
        cards = [card for card in cards if card["size"] > 100]

        card = choice(cards)

        r = await self.bot.http_client.get(card["url"])
        img = b64decode(r.json()["content"])
        file = discord.File(
            fp=BytesIO(img),
            filename=card["path"])

        await self.post(ctx, file, "vampire")


    @commands.command()
    async def neopets(self, ctx):
        await ctx.defer()

        with open("ext/data/neopets.json") as f:
            card = choice(json.load(f))

        r = await self.bot.http_client.get(card)

        card_img = Image.open(BytesIO(r.content)).convert('RGB')

        with BytesIO() as img_binary:
            card_img.save(img_binary, 'PNG')
            img_binary.seek(0)
            file = discord.File(
                fp=img_binary,
                filename=card.rsplit('/', 1)[1].replace('.gif', '.png'))

        await self.post(ctx, file, "neopets")


    @commands.command()
    async def sorcery(self, ctx):
        await ctx.defer()

        # Grab random card
        card_url = "https://api.sorcerytcg.com/api/cards"
        r = await self.bot.http_client.get(card_url)
        card_json = choice(r.json())

        # Get random set printing of the card
        card_set = choice(card_json["sets"])
        card_slug = choice(card_set["variants"])["slug"]

        if card_json["guardian"]["type"] == "Site":
            rotate = True
        else:
            rotate = False

        # Get set folder from Google Drive
        list_url = "https://www.googleapis.com/drive/v3/files"
        list_params = {
            "q": f"name = '{card_slug}.png' and '17IrJkRGmIU9fDSTU2JQEU9JlFzb5liLJ' in parents",
            "key": GOOGLE_KEY
        }
        r = await self.bot.http_client.get(list_url, params=list_params)
        card_id = r.json()["files"][0]["id"]

        #list_params["q"] = f"name = '{card_suffix}' and '{folder_id}' in parents"
        #r = await self.bot.http_client.get(list_url, params=list_params)
        #folder_id = r.json()["files"][0]["id"]

        # Find card id from its set's folder
        #list_params["q"] = f"name = '{card_name}.png' and '{folder_id}' in parents"
        #r = await self.bot.http_client.get(list_url, params=list_params)
        #card_id = r.json()["files"][0]["id"]

        # Get card image data
        get_url = f"https://www.googleapis.com/drive/v3/files/{card_id}"
        get_params = {
            "acknowledgeAbuse": True,
            "alt": "media",
            "key": GOOGLE_KEY
        }
        r = await self.bot.http_client.get(get_url, params=get_params)
        card_img = Image.open(BytesIO(r.content))
        if rotate:
            card_img = card_img.rotate(270, expand=1)

        # Send to Discord
        with BytesIO() as img_binary:
            card_img.save(img_binary, 'PNG')
            img_binary.seek(0)
            file = discord.File(
                fp=img_binary,
                filename=f"{card_slug}.png")

        await self.post(ctx, file, "sorcery")


    @commands.command(aliases=['warcraft'])
    async def wow(self, ctx):
        await ctx.defer()

        # Get Google Drive folder ID from weighted lists
        with open("ext/data/wowtcg.json") as f:
            j = json.load(f)
        set_id = choices(j["sets"], j["weights"])[0]

        # Get card file from folder list
        list_url = "https://www.googleapis.com/drive/v3/files"
        list_params = {
            "q": f"'{set_id}' in parents",
            "pageSize": 500,
            "key": GOOGLE_KEY
        }
        r = await self.bot.http_client.get(list_url, params=list_params)
        card_id = choice(r.json()["files"])["id"]

        # Get card image binary
        get_url = f"https://www.googleapis.com/drive/v3/files/{card_id}"
        get_params = {
            "acknowledgeAbuse": True,
            "alt": "media",
            "key": GOOGLE_KEY
        }
        r = await self.bot.http_client.get(get_url, params=get_params)
        card_img = Image.open(BytesIO(r.content))

        # Send to Discord
        with BytesIO() as img_binary:
            card_img.save(img_binary, 'PNG')
            img_binary.seek(0)
            file = discord.File(
                fp=img_binary,
                filename=f"{card_id}.png")

        await self.post(ctx, file, "warcraft")


    @commands.command()
    async def spellfire(self, ctx):
        await ctx.defer()

        with open ("ext/data/spellfire.json") as f:
            j = json.load(f)
        set_tree = choices(j["sets"], j["weights"])[0]

        url = ("https://api.github.com/repos/dumsantos/Spellfire_EN-BR/"
            f"git/trees/{set_tree}")

        r = await self.bot.http_client.get(url)
        cards = r.json()["tree"]

        cards = [card for card in cards if ".jpg" in card["path"]]
        card = choice(cards)

        r = await self.bot.http_client.get(card["url"])
        img = b64decode(r.json()["content"])
        file = discord.File(
            fp=BytesIO(img),
            filename=card["path"])

        await self.post(ctx, file, "spellfire")


    @commands.command()
    async def shadowverse(self, ctx):
        await ctx.defer()

        with open("ext/data/card/shadowverse.txt") as f:
            cards = f.read().splitlines()
        card = choice(cards)

        #headers = {
        #    "User-Agent": "battlebutt/1.0",
        #}
        base_url = "https://en.shadowverse-evolve.com/wordpress/wp-content/images/cardlist/"
        #r = await self.bot.http_client.get(f"{base_url}{card}.png", headers=headers)
        #await self.bot.get_channel(DEBUG_CHANNEL).send(f"shadowverse {r.status_code}")

        #card_img = Image.open(BytesIO(r.content))

        # Send to Discord
        #with BytesIO() as img_binary:
        #    card_img.save(img_binary, 'PNG')
        #    img_binary.seek(0)
        #    file = discord.File(
        #        fp=img_binary,
        #        filename=f"{card.rsplit('/')[1]}.png")

        await self.post(ctx, f"{base_url}{card}.png", "shadowverse")


    @commands.command(aliases=['swu'])
    async def starwars(self, ctx):
        await ctx.defer()

        base_url = "https://swudb.com"

        r = await self.bot.http_client.get(f"{base_url}/api/card/getRandomCard")

        r = await self.bot.http_client.post(f"{base_url}/api/card/getPrintingInfo",
            json=r.json())

        card = r.json()
        if card["backImagePath"]:
            card_path = choice([card["frontImagePath"], card["backImagePath"]])
        else:
            card_path = card["frontImagePath"]
        if card_path[0] == "~":
            card_path = card_path[1:]
        card_img = f"{base_url}/images{card_path}"

        await self.post(ctx, card_img, "star wars")
            

    @commands.command(aliases=['bs'])
    async def battlespirits(self, ctx):
        await ctx.defer()

        url = "https://api.bandai-tcg-plus.com/api/user/card/list"
        params = {
            "game_title_id": 7,
            "limit": 1,
            "offset": 0
        }
        r = await self.bot.http_client.get(url, params=params)

        count = r.json()["success"]["total"]
        params["offset"] = randint(0, int(count)-1)

        r = await self.bot.http_client.get(url, params=params)
        card = r.json()["success"]["cards"][0]

        if "backcard_image_url" in card:
            card_img = choice([card["image_url"], card["backcard_image_url"]])
        else:
            card_img = card["image_url"]

        await self.post(ctx, card_img, "battle spirits")

    @commands.command()
    async def alphaclash(self, ctx):
        await ctx.defer()

        url = "https://play-api.carde.io/v1/cards/64483da67fc2aee28c8427bf"
        params = {
            "limit": 1
        }
        r = await self.bot.http_client.get(url, params=params)
        pages = r.json()["pagination"]["totalPages"]

        selected_page = randint(1, int(pages))
        params["page"] = selected_page

        r = await self.bot.http_client.get(url, params=params)
        card_img = r.json()["data"][0]["imageUrl"]

        await self.post(ctx, card_img, "alpha clash")


    @commands.command()
    async def altered(self, ctx):
        await ctx.defer()

        url = "https://cards.alteredcore.org/api/cards"
        params = {
            "itemsPerPage": 1,
            "variation[]": "standard",
            "rarity[]": ["COMMON", "RARE", "EXALTED"]
        }
        r = await self.bot.http_client.get(url, params=params)
        pages = r.json()["totalItems"]

        selected_page = randint(1, int(pages))
        params["page"] = selected_page

        r = await self.bot.http_client.get(url, params=params)
        card = r.json()['member'][0]
        card_img = f"https://cdn.alteredcore.org/cards/en/{card['set']['reference']}/{card['reference']}.webp"

        await self.post(ctx, card_img, "altered")


    @commands.command()
    async def elestrals(self, ctx):
        await ctx.defer()

        url = "https://play-api.carde.io/v1/cards/64a31866dd516a3cc4c8d45c"
        params = {
            "limit": 1
        }
        r = await self.bot.http_client.get(url, params=params)
        pages = r.json()["pagination"]["totalPages"]

        selected_page = randint(1, int(pages))
        params["page"] = selected_page

        r = await self.bot.http_client.get(url, params=params)
        card_url = r.json()["data"][0]["imageUrl"]

        r = await self.bot.http_client.get(card_url)

        # Crop borders of card
        card_img = Image.open(BytesIO(r.content))
        card_img = card_img.crop(card_img.getbbox())

        # Send to Discord
        with BytesIO() as img_binary:
            card_img.save(img_binary, 'PNG')
            img_binary.seek(0)
            file = discord.File(
                fp=img_binary,
                filename=card_url.rsplit('/', 1)[1])

        await self.post(ctx, file, "elestrals")

    @commands.command()
    async def fabledsagas(self, ctx):
        await ctx.defer()

        url = "https://play-api.carde.io/v1/cards/64626b9a9d5830157996b180"
        params = {
            "limit": 1
        }
        r = await self.bot.http_client.get(url, params=params)
        pages = r.json()["pagination"]["totalPages"]

        selected_page = randint(1, int(pages))
        params["page"] = selected_page

        r = await self.bot.http_client.get(url, params=params)
        card_img = r.json()["data"][0]["imageUrl"]

        await self.post(ctx, card_img, "fabled sagas")


    @commands.command()
    async def akora(self, ctx):
        await ctx.defer()

        url = "https://play-api.carde.io/v1/cards/636855fc34369ca07c26f17d"
        params = {
            "limit": 1
        }
        r = await self.bot.http_client.get(url, params=params)
        pages = r.json()["pagination"]["totalPages"]

        selected_page = randint(1, int(pages))
        params["page"] = selected_page

        r = await self.bot.http_client.get(url, params=params)
        card_img = r.json()["data"][0]["imageUrl"]

        await self.post(ctx, card_img, "akora")


    @commands.command()
    async def metazoo(self, ctx):
        await ctx.defer()

        url = "https://play-api.carde.io/v1/cards/6362b23bafcb45c0e3070ddf"
        params = {
            "limit": 1
        }
        r = await self.bot.http_client.get(url, params=params)
        pages = r.json()["pagination"]["totalPages"]

        selected_page = randint(1, int(pages))
        params["page"] = selected_page

        r = await self.bot.http_client.get(url, params=params)
        card_img = r.json()["data"][0]["imageUrl"]

        await self.post(ctx, card_img, "akora")


    @commands.command(aliases=['fow'])
    async def forceofwill(self, ctx):
        await ctx.defer()

        url = "https://www.fowtcg.com/card_search"
        params = {
            "_method": "GET"
        }

        r = await self.bot.http_client.get(url, params=params)
        page = html.fromstring(r.text)

        max_pages = page.xpath(
            "//nav[@role='navigation']/div/div/span/a/text()")[-3]
        selected_page = randint(1, int(max_pages))
        params["page"] = selected_page

        r = await self.bot.http_client.get(url, params=params)
        page = html.fromstring(r.text)

        card_img = choice(page.xpath(
            "//li[@class='lg:w-4/12 px-4 text-center my-4']/a/img/@src"))

        await self.post(ctx, card_img, "force of will")


    @commands.command(aliases=['dm', 'duema'])
    async def duelmasters(self, ctx):
        await ctx.defer()

        url = "https://dm.takaratomy.co.jp"
        c_url = url + "/card/"

        data = {
            "pagenum": 1
        }
        r = await self.bot.http_client.post(c_url, data=data)
        page = html.fromstring(r.text)

        card_count = page.xpath("//span[@id='total_count']/text()")[0]
        max_pages = int(int(card_count) / 50) + 1
        data["pagenum"] = randint(1, max_pages)

        r = await self.bot.http_client.post(c_url, data=data)
        page = html.fromstring(r.text)
        card_img = choice(page.xpath("//div[@id='cardlist']/ul/li/a/img/@src"))

        await self.post(ctx, f"{url}/{card_img}", "duel masters")


    @commands.command()
    async def wixoss(self, ctx):
        await ctx.defer()

        url = "https://www.takaratomy.co.jp/products/en.wixoss/card/"
        req_url = url + "itemsearch.php"
        params = {
            "p": 1
        }
        r = await self.bot.http_client.get(req_url, params=params)
        max_pages = int(int(r.json()["count"]) / 20) + 1
        params["p"] = randint(1, max_pages)

        r = await self.bot.http_client.get(req_url, params=params)
        card = choice(r.json()["items"])
        card_img = f"{url}thumb/{card['card_no']}.jpg"

        await self.post(ctx, card_img, "wixoss")


    @commands.command()
    async def lightseekers(self, ctx):
        await ctx.defer()

        url = "https://carddatabase-es.lightseekers.cards/lightseekers-cards/_search"
        data = {
            "size": 1,
            "sort": [{"name.normalized": "asc"}]
        }
        r = await self.bot.http_client.post(url, json=data)

        card_count = r.json()["hits"]["total"]
        data["from"] = randint(0, card_count-1)

        r = await self.bot.http_client.post(url, json=data)
        card = r.json()["hits"]["hits"][0]

        card_sku = choice([sku for sku in card["_source"]["skus"] if sku["image"]])
        card_img = f"https://assets.lightseekers.cards/card-database/cards/{card_sku['id']}.jpg"

        await self.post(ctx, card_img, "lightseekers")


    @commands.command()
    async def tombraider(self, ctx):

        params = {
            "action": "query",
            "list": "categorymembers",
            "cmtitle": "Category:Cards",
            "cmlimit": "500",
            "format": "json"
        }
        url = "https://www.wikiraider.tombraidergirl.net/api.php"

        finished = False
        article_list = []
        while not finished:
            r = await self.bot.http_client.get(url, 
                params=params)
            results = r.json()

            if "continue" in results:
                params["cmcontinue"] = results["continue"]["cmcontinue"]
            else:
                finished = True

            for c in results["query"]["categorymembers"]:
                if c["ns"] == 0 and c["pageid"] != 4052:
                    article_list.append(c["title"])

        selected_article = choice(article_list)
        await self.bot.get_channel(DEBUG_CHANNEL).send(f"tombraider {selected_article}")
        params = {
            "action": "parse",
            "page": selected_article,
            "format": "json"
        }
        r = await self.bot.http_client.get(url,
            params=params, timeout=15)
        page = html.fromstring(r.json()["parse"]["text"]["*"].replace('\"','"'))

        card_path = page.xpath("//tr/td/a[@class='image']/@href")[0].replace(
            'File:', 'Special:FilePath/')
        card_img = f"{url.rsplit('/', 1)[0]}{card_path}"

        await self.post(ctx, card_img, "tomb raider")

    @commands.command()
    async def ageofsigmar(self, ctx):
        card_img = await self.tcgplayer_rand("warhammer-age-of-sigmar-champions-tcg")        
        await self.post(ctx, card_img, "age of sigmar")


    @commands.command(aliases=['zwo'])
    async def zombieworldorder(self, ctx):
        card_img = await self.tcgplayer_rand("zombie-world-order-tcg")
        await self.post(ctx, card_img, "zombie world order")


    @commands.command()
    async def vividz(self, ctx):
        await ctx.defer()

        url = f"https://vividztcg.com/card/?search=1&pg={randint(1,48)}"
        r = await self.bot.http_client.get(url)
        page = html.fromstring(r.text)

        card_img = choice(page.xpath("//ul[@class='list']/li/img/@src"))

        await self.post(ctx, card_img, "vividz")


    @commands.command()
    async def onepiece(self, ctx):
        await ctx.defer()

        # Get Google Drive folder ID from weighted lists
        with open("ext/data/optcg.json") as f:
            j = json.load(f)
        sets = list(j.keys())
        weights = []
        for s in sets:
            weights.append(j[s])

        set_id = choices(sets, weights)[0]

        # Get card file from folder list
        list_url = "https://www.googleapis.com/drive/v3/files"
        list_params = {
            "q": f"'{set_id}' in parents",
            "pageSize": 500,
            "key": GOOGLE_KEY
        }
        r = await self.bot.http_client.get(list_url, params=list_params)
        found_valid = False
        while not found_valid:
            card = choice(r.json()["files"])
            if "image" in card["mimeType"] and "Playmat" not in card["name"]:
                found_valid = True

        # Get card image binary
        get_url = f"https://www.googleapis.com/drive/v3/files/{card['id']}"
        get_params = {
            "acknowledgeAbuse": True,
            "alt": "media",
            "key": GOOGLE_KEY
        }
        r = await self.bot.http_client.get(get_url, params=get_params)
        card_img = Image.open(BytesIO(r.content))

        # Send to Discord
        with BytesIO() as img_binary:
            if "jpeg" in  card["mimeType"]:
                card_img.save(img_binary, "JPEG")
            else:
                card_img.save(img_binary, 'PNG')
            img_binary.seek(0)
            file = discord.File(
                fp=img_binary,
                filename=card['name'])

        await self.post(ctx, file, "one piece")


    @commands.command()
    async def wyvern(self, ctx):

        with open("ext/data/wyvern.json") as f:
            j = json.load(f)
        card = choice(j)

        await self.post(ctx, f"https://api.ccgtrader.co.uk{card}", "wyvern")


    @commands.command()
    async def bellasara(self, ctx):

        with open("ext/data/bellasara.json") as f:
            j = json.load(f)
        card = choice(j)

        await self.post(ctx, f"https://bellasara.wiki.gg/wiki/Special:FilePath/{card}", "bella sara")

    @commands.command()
    async def hololive(self, ctx):
        await ctx.defer()

        url = "https://en.hololive-official-cardgame.com"

        r = await self.bot.http_client.get(f"{url}/cardlist/cardsearch")
        page = html.fromstring(r.text)

        card_count = int(page.xpath("//span[@class='num bold']/text()")[0])
        selected_page = randint(1, int(card_count/15)+1)

        params = {
            "view": "image",
            "page": selected_page
        }
        r = await self.bot.http_client.get(f"{url}/cardlist/cardsearch_ex", params=params)
        page = html.fromstring(r.text)

        card_img = choice(page.xpath("//li/a/img/@src"))
        await self.post(ctx, f"{url}{card_img}", "hololive")


    @commands.command()
    async def grottobeasts(self, ctx):

        url = f"https://grottobeasts.gitlab.io/assets/img/newcards/GB{randint(1,200):03d}.png"

        await self.post(ctx, url, "grotto beasts")


    @commands.command()
    async def riftbound(self, ctx):
        await ctx.defer()

        card = await self.carde_rand(3)
        r = await self.bot.http_client.get(card["image_url"])

        card_img = Image.open(BytesIO(r.content))
        if "Battlefield" in card["card_type"]:
            card_img = card_img.rotate(270, expand=1)

        # Send to Discord
        with BytesIO() as img_binary:
            card_img.save(img_binary, 'WEBP')
            img_binary.seek(0)
            file = discord.File(
                fp=img_binary,
                filename=f"{card['collector_number']}.webp")

        await self.post(ctx, file, "riftbound")
    

    @commands.command()
    async def genesis(self, ctx):
        await ctx.defer()

        url = "https://www.genesisbattleofchampions.com"
        r = await self.bot.http_client.get(f"{url}/library")
        page = html.fromstring(r.text)

        chosen_set = choice(page.xpath("//figure/a/@href"))

        r = await self.bot.http_client.get(f"{url}{chosen_set}")
        page = html.fromstring(r.text)

        card_url = choice(page.xpath("//div/a/img/@data-src"))
        await self.post(ctx, card_url, "genesis: battle of champions")


    @commands.command()
    async def palworld(self, ctx):
        await ctx.defer()

        url = "https://palworldtcg.gg"
        params = {
            "per_page": 1,
        }
        r = await self.bot.http_client.get(f"{url}/api/v1/cards", params=params)

        card_count = r.json()["meta"]["total_pages"]
        params["page"] = randint(1, card_count)

        r = await self.bot.http_client.get(f"{url}/api/v1/cards", params=params)
        card_img = r.json()["data"][0]["image_url"]

        await self.post(ctx, f"{url}{card_img}", "palworld")


    @commands.command()
    async def cyberpunk(self, ctx):
        await ctx.defer()

        card = await self.netdeck_rand("cyberpunk")
        await self.post(ctx, card["image_url"], "cyberpunk")


    @commands.command()
    async def finalfantasy(self, ctx):
        await ctx.defer()

        url = "https://storage.googleapis.com/materiahunter-prod.appspot.com"
        cards = self.check_cache("fftcg")
        if not cards:
            r = await self.bot.http_client.get(
                f"{url}/json/card-variantsV2.json")

            cards = list(set([
                f"{url}/images/cards/fftcg/en/{c['imageId']}.jpg"
                for c in r.json()]))

            self.write_cache("fftcg", cards)

        card_img = choice(cards)

        await self.post(ctx, card_img, "final fantasy")


    @commands.command()
    async def cataclysmarcade(self, ctx):
        await ctx.defer()

        card = await self.netdeck_rand("ca")
        await self.post(ctx, card["image_url"], "cataclysm arcade")


    @commands.command()
    async def neuroscape(self, ctx):
        await ctx.defer()

        card = await self.carde_rand(134)
        await self.post(ctx, card["image_url"], "neuroscape")


    @commands.command()
    async def vibes(self, ctx):
        await ctx.defer()

        card = await self.netdeck_rand("vibes")
        await self.post(ctx, card["image_url"], "vibes")


    @commands.command(hidden=True)
    async def playingcard(self, ctx):
        url = "https://www.deckofcardsapi.com/api/deck/new/draw/"
        params = {
            "count": 1,
            "jokers_enabled": True
        }
        r = await self.bot.http_client.get(url, params=params)

        card_img = r.json()["cards"][0]["image"]

        await self.post(ctx, card_img, "card")


async def setup(bot):
    await bot.add_cog(Card(bot))