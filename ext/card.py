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
        """ Pulls a TCG card """
        
        commands = self.get_commands()
        selected_comm = next((
            c for c in commands if c.name == game or game in c.aliases), None)
        if ctx.interaction:
            ctx.interaction.extras = {"rando": False}
        if not selected_comm:
            selected_comm = choice(commands)
            await self.bot.get_channel(DEBUG_CHANNEL).send(selected_comm.name)
            if ctx.interaction:
                ctx.interaction.extras["rando"] = True
        await selected_comm.__call__(ctx, reason)


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


    @commands.command(aliases=['poke'])
    async def pokemon(self, ctx, reason: Optional[str] = None):
        """ Pulls a Pokemon TCG card """
        await ctx.defer()

        url = "https://pkmncards.com/?random"
        r = await self.bot.http_client.get(url, follow_redirects=True)

        # Scrape image from page metadata
        page = html.fromstring(r.text)
        image_url = page.xpath("//meta[@property='og:image']/@content")[0]
        image_url = image_url.split('?')[0]

        if reason and ctx.interaction:
            await ctx.send(f"{'card' if ctx.interaction.extras['rando'] else 'pokemon'} {reason}: [⠀]({image_url})")
        else:
            await ctx.send(image_url)


    @commands.command(aliases=['ygo', 'yugi'])
    async def yugioh(self, ctx, reason: Optional[str] = None):
        """ Pulls a Yu-Gi-Oh! card """
        await ctx.defer()

        url = "https://db.ygoprodeck.com/api/v7/cardinfo.php"
        params = {
            "num": 1, "offset": 0, "sort": "random", "cachebust": 1
        }
        r = await self.bot.http_client.get(url, params=params)
        card = r.json()["data"][0]

        if reason and ctx.interaction:
            await ctx.send(f"{'card' if ctx.interaction.extras['rando'] else 'pokemon'} {reason}: [⠀]({card['card_images'][0]['image_url']})")
        else:
            await ctx.send(card['card_images'][0]['image_url'])


    @commands.command()
    async def digimon(self, ctx, reason: Optional[str] = None):
        """ Pulls a Digimon card. """
        await ctx.defer()

        # Git tree for cardlist, updated 2025/07/10
        tree = "00bef43e2222b3635dd69da0271a840c90a7986c"
        url = ("https://api.github.com/repos/TakaOtaku/"
            f"Digimon-Cards/git/trees/{tree}")
        r = await self.bot.http_client.get(url)
        cards = r.json()["tree"]

        filters = ["-J.", "-j", "-Sample"]
        cards = [card for card in cards if not any(f in card["path"] for f in filters)]
        card = choice(cards)

        r = await self.bot.http_client.get(card["url"])
        img = b64decode(r.json()["content"])
        file = discord.File(
            fp=BytesIO(img),
            filename=card["path"])

        if reason and ctx.interaction:
            await ctx.send(f"{'card' if ctx.interaction.extras['rando'] else 'digimon'} {reason}:", file=file)
        else:
            await ctx.send(file=file)



    @commands.command(aliases=['magic'])
    async def mtg(self, ctx, reason: Optional[str] = None):
        """ Pulls a Magic the Gathering card """
        await ctx.defer()

        url = "https://api.scryfall.com/cards/random"
        r = await self.bot.http_client.get(url)
        card = r.json()

        # If it doesn't have an image then try again
        card_status = card['image_status']
        if card_status == 'missing' or card_status == 'placeholder':
            await self.mtg(ctx)
        else:
            # If card has two sides, pick one side
            if not "image_uris" in card and "card_faces" in card:
                card['image_uris'] = card['card_faces'][randint(0,1)]['image_uris']
            
            if reason and ctx.interaction:
                await ctx.send(f"{'card' if ctx.interaction.extras['rando'] else 'magic'} {reason}: [⠀]({card['image_uris']['border_crop']})")
            else:
                await ctx.send(card['image_uris']['border_crop'])


    @commands.command(aliases=['fab'])
    async def fleshandblood(self, ctx, reason: Optional[str] = None):
        """ Pulls a Flesh and Blood card """
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

        if reason and ctx.interaction:
            await ctx.send(f"{'card' if ctx.interaction.extras['rando'] else 'flesh and blood'} {reason}: [⠀]({card['image']['large']})")
        else:
            await ctx.send(card["image"]["large"])


    @commands.command()
    async def gateruler(self, ctx, reason: Optional[str] = None):
        """ Pulls a Gate Ruler card """
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

        if reason and ctx.interaction:
            await ctx.send(f"{'card' if ctx.interaction.extras['rando'] else 'gate ruler'} {reason}:", file=file)
        else:
            await ctx.send(file=file)
  


    @commands.command(aliases=["cfv", "vanguard", "cardfight"])
    async def cardfightvanguard(self, ctx, reason: Optional[str] = None):
        """ Pulls a Cardfight!! Vanguard card """
        await ctx.defer()

        # Get first page to figure out max page
        url = "https://en.cf-vanguard.com/cardlist/cardsearch"
        r = await self.bot.http_client.get(url)
        page = html.fromstring(r.text)

        # 24 cards per page
        card_count = page.xpath("//div[@class='number']/text()")[0]
        card_count = int(card_count[:-8])
        params = {
            "page": randint(1, int((card_count / 24) + 1))
        }

        # Get page with cards to pick
        r = await self.bot.http_client.get(url, params=params)
        page = html.fromstring(r.text)

        # Pick card
        card = "https://en.cf-vanguard.com{}".format(
            choice(page.xpath("//img[@class='object-fit-img']/@src")))

        if reason and ctx.interaction:
            await ctx.send(f"{'card' if ctx.interaction.extras['rando'] else 'cardfight vanguard'} {reason}: [⠀]({card})")
        else:
            await ctx.send(card)

    @commands.command()
    async def grandarchive(self, ctx, reason: Optional[str] = None):
        """ Pulls a Grand Archive card """
        await ctx.defer()

        r = await self.bot.http_client.get(
            "https://api.gatcg.com/cards/random?amount=1")
        card = r.json()[0]
        card_slug = choice(card["editions"])["slug"]
        card_url = f"https://ga-index-public.s3.us-west-2.amazonaws.com/cards/{card_slug}.jpg"
        
        if reason and ctx.interaction:
            await ctx.send(f"{'card' if ctx.interaction.extras['rando'] else 'grand archive'} {reason}: [⠀]({card_url})")
        else:
            await ctx.send(card_url)


    @commands.command()
    async def nostalgix(self, ctx, reason: Optional[str] = None):
        """ Pulls a Nostalgix card """
        await ctx.defer()

        url = "https://play-api.carde.io/v1/cards/63bc844c3e8d2f34e312bc77"

        r = await self.bot.http_client.get(url)
        max_pages = r.json()["pagination"]["totalPages"]

        params = { "page": randint(1, int(max_pages)) }

        r = await self.bot.http_client.get(url, params=params)
        cards = r.json()["data"]
        card_img = choice(cards)["imageUrl"]

        if reason and ctx.interaction:
            await ctx.send(f"{'card' if ctx.interaction.extras['rando'] else 'nostalgix'} {reason}: [⠀]({card_img})")
        else:
            await ctx.send(card_img)


    @commands.command()
    async def lorcana(self, ctx, reason: Optional[str] = None):
        """ Pulls a Lorcana card """
        await ctx.defer()

        r = await self.bot.http_client.get("https://api.lorcana-api.com/bulk/cards")
        cards = r.json()
        card_img = choice(cards)["Image"]

        if reason and ctx.interaction:
            await ctx.send(f"{'card' if ctx.interaction.extras['rando'] else 'lorcana'} {reason}: [⠀]({card_img})")
        else:
            await ctx.send(card_img)


    @commands.command()
    async def redemption(self, ctx, reason: Optional[str] = None):
        """ Pulls a Redemption card """
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

        if reason and ctx.interaction:
            await ctx.send(f"{'card' if ctx.interaction.extras['rando'] else 'redemption'} {reason}:", file=file)
        else:
            await ctx.send(file=file)


    @commands.command()
    async def vampire(self, ctx, reason: Optional[str] = None):
        """ Pulls a Vampire: The Eternal Struggle card """
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

        if reason and ctx.interaction:
            await ctx.send(f"{'card' if ctx.interaction.extras['rando'] else 'vampire'} {reason}:", file=file)
        else:
            await ctx.send(file=file)


    @commands.command()
    async def neopets(self, ctx, reason: Optional[str] = None):
        """ Pulls a Neopets card """
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

        if reason and ctx.interaction:
            await ctx.send(f"{'card' if ctx.interaction.extras['rando'] else 'neopets'} {reason}:", file=file)
        else:
            await ctx.send(file=file)



    @commands.command()
    async def sorcery(self, ctx, reason: Optional[str] = None):
        """ Pulls a Sorcery card """
        await ctx.defer()

        # Grab random card
        card_url = "https://api.sorcerytcg.com/api/cards"
        r = await self.bot.http_client.get(card_url)
        card_json = choice(r.json())

        # Get random set printing of the card
        card_set = choice(card_json["sets"])
        set_name = card_set["name"]

        # Get random variant, strip set affix and grab suffix
        # Card slug format: set_cardname_location_variant
        card_name = choice(card_set["variants"])["slug"].split("_", 1)[1]
        card_suffix = "_".join(card_name.rsplit("_", 2)[-2:])

        if card_json["guardian"]["type"] == "Site":
            rotate = True
        else:
            rotate = False

        # Get set folder from Google Drive
        list_url = "https://www.googleapis.com/drive/v3/files"
        list_params = {
            "q": f"name = '{set_name}' and '17IrJkRGmIU9fDSTU2JQEU9JlFzb5liLJ' in parents",
            "key": GOOGLE_KEY
        }
        r = await self.bot.http_client.get(list_url, params=list_params)
        folder_id = r.json()["files"][0]["id"]

        list_params["q"] = f"name = '{card_suffix}' and '{folder_id}' in parents"
        r = await self.bot.http_client.get(list_url, params=list_params)
        folder_id = r.json()["files"][0]["id"]

        # Find card id from its set's folder
        list_params["q"] = f"name = '{card_name}.png' and '{folder_id}' in parents"
        r = await self.bot.http_client.get(list_url, params=list_params)
        card_id = r.json()["files"][0]["id"]

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
                filename=f"{card_name}.png")

        if reason and ctx.interaction:
            await ctx.send(f"{'card' if ctx.interaction.extras['rando'] else 'sorcery'} {reason}:", file=file)
        else:
            await ctx.send(file=file)



    @commands.command(aliases=['warcraft'])
    async def wow(self, ctx, reason: Optional[str] = None):
        """ Pulls a World of Warcraft TCG card """
        await ctx.defer()

        # Get Google Drive folder ID from weighted lists
        with open("ext/data/wowtcg.json") as f:
            j = json.load(f)
        set_id = choices(j["sets"], j["weights"])[0]

        # Get card file from folder list
        list_url = "https://www.googleapis.com/drive/v3/files"
        list_params = {
            "q": f"'{set_id}' in parents",
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

        if reason and ctx.interaction:
            await ctx.send(f"{'card' if ctx.interaction.extras['rando'] else 'warcraft'} {reason}:", file=file)
        else:
            await ctx.send(file=file)



    @commands.command()
    async def spellfire(self, ctx, reason: Optional[str] = None):
        """ Pulls a Spellfire card """
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

        if reason and ctx.interaction:
            await ctx.send(f"{'card' if ctx.interaction.extras['rando'] else 'spellfire'} {reason}:", file=file)
        else:
            await ctx.send(file=file)



    @commands.command()
    async def shadowverse(self, ctx, reason: Optional[str] = None):
        """ Pulls a Shadowverse: Evolve card """
        await ctx.defer()

        # Get max card count
        url = "https://en.shadowverse-evolve.com/cards/searchresults/"
        r = await self.bot.http_client.get(url)
        page = html.fromstring(r.text)

        # 15 cards per page
        card_count = page.xpath("//span[@class='num bold']/text()")[0]
        card_count = int(card_count)
        params = {
            "page": randint(1, int((card_count / 15) + 1))
        }

        # Get page with cards to pick
        r = await self.bot.http_client.get(url, params=params)
        page = html.fromstring(r.text)

        # Pick card
        card = "https://en.shadowverse-evolve.com{}".format(
            choice(page.xpath("//img[@class='object-fit-img']/@src")))

        if reason and ctx.interaction:
            await ctx.send(f"{'card' if ctx.interaction.extras['rando'] else 'shadowverse'} {reason}: [⠀]({card})")
        else:
            await ctx.send(card)


    @commands.command(aliases=['swu'])
    async def starwars(self, ctx, reason: Optional[str] = None):
        """ Pulls a Star Wars Unlimited card """
        await ctx.defer()

        base_url = "https://swudb.com"

        r = await self.bot.http_client.get(f"{base_url}/api/card/getRandomCard")

        r = await self.bot.http_client.post(f"{base_url}/api/card/getVariantInfo",
            json=r.json())

        card = r.json()
        if card["backImagePath"]:
            card_path = choice([card["frontImagePath"], card["backImagePath"]])
        else:
            card_path = card["frontImagePath"]
        card_img = f"{base_url}/images{card_path[1:]}"

        if reason and ctx.interaction:
            await ctx.send(f"{'card' if ctx.interaction.extras['rando'] else 'star wars'} {reason}: [⠀]({card_img})")
        else:
            await ctx.send(card_img)
            

    @commands.command(aliases=['bs'])
    async def battlespirits(self, ctx, reason: Optional[str] = None):
        """ Pulls a Battle Spirits card """
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

        if reason and ctx.interaction:
            await ctx.send(f"{'card' if ctx.interaction.extras['rando'] else 'battle spirits'} {reason}: [⠀]({card_img})")
        else:
            await ctx.send(card_img)



    @commands.command()
    async def alphaclash(self, ctx, reason: Optional[str] = None):
        """ Pulls an Alpha Clash card """
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

        if reason and ctx.interaction:
            await ctx.send(f"{'card' if ctx.interaction.extras['rando'] else 'alpha clash'} {reason}: [⠀]({card_img})")
        else:
            await ctx.send(card_img)


    @commands.command()
    async def altered(self, ctx, reason: Optional[str] = None):
        """ Pulls an Altered TCG card """
        await ctx.defer()

        url = "https://api.altered.gg/cards"
        params = {
            "itemsPerPage": 1
        }
        r = await self.bot.http_client.get(url, params=params)
        pages = r.json()["hydra:totalItems"]

        selected_page = randint(1, int(pages))
        params["page"] = selected_page

        r = await self.bot.http_client.get(url, params=params)
        card_img = r.json()["hydra:member"][0]["imagePath"]

        if reason and ctx.interaction:
            await ctx.send(f"{'card' if ctx.interaction.extras['rando'] else 'altered'} {reason}: [⠀]({card_img})")
        else:
            await ctx.send(card_img)


    @commands.command()
    async def elestrals(self, ctx, reason: Optional[str] = None):
        """ Pulls an Elestrals card """
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

        if reason and ctx.interaction:
            await ctx.send(f"{'card' if ctx.interaction.extras['rando'] else 'elestrals'} {reason}:", file=file)
        else:
            await ctx.send(file=file)

    @commands.command()
    async def fabledsagas(self, ctx, reason: Optional[str] = None):
        """ Pulls a Fabled Sagas card """
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

        if reason and ctx.interaction:
            await ctx.send(f"{'card' if ctx.interaction.extras['rando'] else 'fabled sagas'} {reason}: [⠀]({card_img})")
        else:
            await ctx.send(card_img)

    @commands.command()
    async def akora(self, ctx, reason: Optional[str] = None):
        """ Pulls an Akora card """
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

        if reason and ctx.interaction:
            await ctx.send(f"{'card' if ctx.interaction.extras['rando'] else 'akora'} {reason}: [⠀]({card_img})")
        else:
            await ctx.send(card_img)


    @commands.command()
    async def metazoo(self, ctx, reason: Optional[str] = None):
        """ Pulls a MetaZoo card """
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

        if reason and ctx.interaction:
            await ctx.send(f"{'card' if ctx.interaction.extras['rando'] else 'metazoo'} {reason}: [⠀]({card_img})")
        else:
            await ctx.send(card_img)


    @commands.command(aliases=['fow'])
    async def forceofwill(self, ctx, reason: Optional[str] = None):
        """ Pulls a Force of Will card """
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

        if reason and ctx.interaction:
            await ctx.send(f"{'card' if ctx.interaction.extras['rando'] else 'force of will'} {reason}: [⠀]({card_img})")
        else:
            await ctx.send(card_img)


    @commands.command(aliases=['dm', 'duema'])
    async def duelmasters(self, ctx, reason: Optional[str] = None):
        """ Pulls a Japanese Duel Masters card """
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

        if reason and ctx.interaction:
            await ctx.send(f"{'card' if ctx.interaction.extras['rando'] else 'duel masters'} {reason}: [⠀]({url}/{card_img})")
        else:
            await ctx.send(f"{url}/{card_img}")


    @commands.command()
    async def wixoss(self, ctx, reason: Optional[str] = None):
        """ Pulls a Wixoss card """
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

        if reason and ctx.interaction:
            await ctx.send(f"{'card' if ctx.interaction.extras['rando'] else 'wixoss'} {reason}: [⠀]({card_img})")
        else:
            await ctx.send(card_img)


    @commands.command()
    async def lightseekers(self, ctx, reason: Optional[str] = None):
        """ Pulls a Lightseekers card """
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

        if reason and ctx.interaction:
            await ctx.send(f"{'card' if ctx.interaction.extras['rando'] else 'lightseekers'} {reason}: [⠀]({card_img})")
        else:
            await ctx.send(card_img)


    @commands.command()
    async def tombraider(self, ctx, reason: Optional[str] = None):
        """ Pulls a Tomb Raider card """

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

        if reason and ctx.interaction:
            await ctx.send(f"{'card' if ctx.interaction.extras['rando'] else 'tomb raider'} {reason}: [⠀]({card_img})")
        else:
            await ctx.send(card_img)


    @commands.command()
    async def ageofsigmar(self, ctx, reason: Optional[str] = None):
        """ Pulls a Warhammer Age of Sigmar card """

        url = "https://mp-search-api.tcgplayer.com/v1/search/request"
        data = {
            "filters": {
                "term" : {
                    "productLineName": ["warhammer-age-of-sigmar-champions-tcg"],
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
        data["from"] = randint(0, card_count-1)

        r = await self.bot.http_client.post(url, json=data)
        card = r.json()["results"][0]["results"][0]

        card_id = int(card["productId"])
        card_img = f"https://tcgplayer-cdn.tcgplayer.com/product/{card_id}_in_1000x1000.jpg"
        
        if reason and ctx.interaction:
            await ctx.send(f"{'card' if ctx.interaction.extras['rando'] else 'age of sigmar'} {reason}: [⠀]({card_img})")
        else:
            await ctx.send(card_img)


    @commands.command(aliases=['zwo'])
    async def zombieworldorder(self, ctx, reason: Optional[str] = None):
        """ Pulls a Warhammer Age of Sigmar card """

        url = "https://mp-search-api.tcgplayer.com/v1/search/request"
        data = {
            "filters": {
                "term" : {
                    "productLineName": ["zombie-world-order-tcg"],
                    "productTypeName": ["Cards"]
                }
            },
            "size": 1,
            "from": randint(0,68),
            "sort": {
                "field": "product-sorting-name",
                "order": "asc"
            }
        }
        r = await self.bot.http_client.post(url, json=data)

        card = r.json()["results"][0]["results"][0]

        card_id = int(card["productId"])
        card_img = f"https://tcgplayer-cdn.tcgplayer.com/product/{card_id}_in_1000x1000.jpg"
        
        if reason and ctx.interaction:
            await ctx.send(f"{'card' if ctx.interaction.extras['rando'] else 'zombie world orderr'} {reason}: [⠀]({card_img})")
        else:
            await ctx.send(card_img)


    @commands.command()
    async def vcard(self, ctx, reason: Optional[str] = None):
        """ Pulls a VCard """
        await ctx.defer()

        url = "https://www.vcardtcg.com/cards"
        headers = {
            "Next-Action": "003a7707433d51c83145d3bf14c20620319348d78d"
        }
        data = []

        r = await self.bot.http_client.post(url, json=data, headers=headers)
        results = json.loads(r.text.split('\n', 1)[1][2:])

        cards = []
        for rarity in results.values():
            if rarity[0]["cardType"] != "TYPE#BOX_TOPPER":
                cards.extend(rarity)

        card = choice(cards)
        card_url = choice(list(card["variants"].values()))["url"]
        r = await self.bot.http_client.get(card_url)

        # Crop borders of card
        card_img = Image.open(BytesIO(r.content))

        with BytesIO() as img_binary:
            if ".jpeg" in card_url or ".webp" in card_url:
                card_img = card_img.crop((41, 41, 898, 1239))
                card_img.save(img_binary, 'JPEG')
            else:
                card_img = card_img.crop((25, 25, 563, 776))
                card_img.save(img_binary, 'PNG')
            img_binary.seek(0)
            file = discord.File(
                fp=img_binary,
                filename=card_url.rsplit('/', 1)[1])

        if reason and ctx.interaction:
            await ctx.send(f"{'card' if ctx.interaction.extras['rando'] else 'vcard'} {reason}:", file=file)
        else:
            await ctx.send(file=file)


    @commands.command()
    async def vividz(self, ctx, reason: Optional[str] = None):
        """ Pulls a Vividz card """
        await ctx.defer()

        url = f"https://vividztcg.com/card/?search=1&pg={randint(1,48)}"
        r = await self.bot.http_client.get(url)
        page = html.fromstring(r.text)

        card_img = choice(page.xpath("//ul[@class='list']/li/img/@src"))

        if reason and ctx.interaction:
            await ctx.send(f"{'card' if ctx.interaction.extras['rando'] else 'vividz'} {reason}: [⠀](https://vividztcg.com{card_img})")
        else:
            await ctx.send(f"https://vividztcg.com{card_img}")

    @commands.command(hidden=True)
    async def playingcard(self, ctx):

        r = await self.bot.http_client.get(
            "https://www.deckofcardsapi.com/api/deck/new/draw/?count=1&jokers_enabled=True")

        await ctx.send(r.json()["cards"][0]["image"])


async def setup(bot):
    await bot.add_cog(Card(bot))