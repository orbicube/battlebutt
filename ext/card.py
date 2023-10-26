import discord
from discord import app_commands
from discord.ext import commands

from typing import Optional
from random import choice, randint

from lxml import html
from PIL import Image
from io import BytesIO
from base64 import b64decode

from credentials import DEBUG_CHANNEL

class Card(commands.Cog,
    command_attrs={"cooldown": commands.CooldownMapping.from_cooldown(
        1, 30, commands.BucketType.user)}):

    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command()
    @app_commands.describe(game="TCG you want to pull a card from")
    async def card(self, ctx, game: Optional[str] = None):
        """ Pulls a random TCG card """

        if game:
            if game.startswith("poke"):
                await self.pokemon(ctx)
            elif game.startswith(("yugioh", "ygo")):
                await self.yugioh(ctx)
            elif game.startswith(("mtg", "magic")):
                await self.mtg(ctx)
            elif game.startswith("digi"):
                await self.digimon(ctx)
            elif game.startswith(("flesh", "fab")):
                await self.fleshandblood(ctx)
            elif game.startswith("gateruler"):
                await self.gateruler(ctx)
            elif game.startswith(("finalfantasy", "fftcg")):
                await self.finalfantasy(ctx)
            elif game.startswith(("cardfightvanguard", "cfv")):
                await self.cardfightvanguard(ctx)
            elif game.startswith("grandarchive"):
                await self.grandarchive(ctx)
            elif game.startswith("nostalg"):
                await self.nostalgix(ctx)
            elif game.startswith("lorcana"):
                await self.lorcana(ctx)
            elif game.startswith("redemption"):
                await self.redemption(ctx)
            elif game.startswith("vampire"):
                await self.vampire(ctx)
            else:
                command = choice(self.get_commands())
                await command.__call__(ctx)
        else:
            command = choice(self.get_commands())
            await command.__call__(ctx)

    @card.autocomplete('game')
    async def card_autocomplete(self, 
        interaction: discord.Interaction,
        current: str,) -> list[app_commands.Choice[str]]:
        
        games = ['pokemon', 'yugioh', 'magic', 'digimon',
            'fleshandblood', 'gateruler', 'finalfantasy',
            'cardfightvanguard', 'grandarchive', 'nostalgix',
            'lorcana', 'redemption', 'vampire']

        return [app_commands.Choice(name=game, value=game)
            for game in games if current.lower() in game.lower() ] 


    @commands.command(aliases=['poke'])
    async def pokemon(self, ctx):
        """ Pulls a random Pokemon TCG card """

        url = "https://pkmncards.com/?random"
        r = await self.bot.http_client.get(url, follow_redirects=True)

        # Scrape image from page metadata
        page = html.fromstring(r.text)
        image_url = page.xpath("//meta[@property='og:image']/@content")[0]
        image_url = image_url.split('?')[0]

        await ctx.send(image_url)


    @commands.command(aliases=['ygo'])
    async def yugioh(self, ctx):
        """ Pulls a random Yu-Gi-Oh! card """
       
        url = "https://db.ygoprodeck.com/api/v7/randomcard.php"
        r = await self.bot.http_client.get(url)
        card = r.json()

        await ctx.send(card['card_images'][0]['image_url'])


    @commands.command()
    async def digimon(self, ctx):
        """ Pulls a random Digimon card. """

        url = ("https://digimoncard.io/api-public/"
            "getAllCards.php?series=Digimon%20Card%20Game")
        r = await self.bot.http_client.get(url)
        card_list = r.json()

        await ctx.send(("https://images.digimoncard.io/images/cards/"
            f"{choice(card_list)['cardnumber']}.jpg"))


    @commands.command(aliases=['magic'])
    async def mtg(self, ctx):
        """ Pulls a random Magic the Gathering card """

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
            
            await ctx.send(card['image_uris']['border_crop'])


    @commands.command(aliases=['fab'])
    async def fleshandblood(self, ctx):
        """ Pulls a random Flesh and Blood card """

        url = "https://api.fabdb.net/cards"
        r = await self.bot.http_client.get(url)
        page = r.json()

        # Pick random page
        page_select = randint(1, page['meta']['last_page'])        
        params = { "page": page_select }

        # Get random card from random page
        r = await self.bot.http_client.get(url, params=params)
        page = r.json()
        card = choice(page['data'])

        await ctx.send(card['image'].split('?')[0])


    @commands.command()
    async def gateruler(self, ctx):
        """ Pulls a random Gate Ruler card """

        # Defer in case edit takes too long
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
            await ctx.send(file=discord.File(
                fp=img_binary,
                filename=card_url.rsplit('/', 1)[1]))


    @commands.command(aliases=['fftcg'])
    async def finalfantasy(self, ctx):
        """ Pulls a random Final Fantasy TCG card """

        # Defer in case JSON download takes too long
        await ctx.defer()

        url = "https://fftcg.square-enix-games.com/na/get-cards"
        r = await self.bot.http_client.get(url)           
        cards = r.json()

        card = choice(cards['cards'])
        if '\/' in card['code']:
            card['code'] = card['code'].split('\/')[0]

        await ctx.send(("https://fftcg.cdn.sewest.net/images/cards/"
            f"full/{card['code']}_eg.jpg"))


    @commands.command(aliases=["cfvangaurd", "cfv"])
    async def cardfightvanguard(self, ctx):
        """ Pulls a random Cardfight!! Vanguard card """

        # Defer in case multiple requests take too long
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
        await ctx.send(card)


    @commands.command()
    async def grandarchive(self, ctx):
        """ Pulls a random Grand Archive card """

        r = await self.bot.http_client.get(
            "https://api.gatcg.com/cards/random?amount=1")
        card = r.json()[0]
        card_slug = choice(card["editions"])["slug"]

        await ctx.send(f"https://ga-index-public.s3.us-west-2.amazonaws.com/cards/{card_slug}.jpg")


    @commands.command()
    async def nostalgix(self, ctx):
        """ Pulls a random Nostalgix card """

        url = "https://play-api.carde.io/v1/cards/63bc844c3e8d2f34e312bc77"

        r = await self.bot.http_client.get(url)
        max_pages = r.json()["pagination"]["totalPages"]

        params = { "page": randint(1, int(max_pages)) }

        r = await self.bot.http_client.get(url, params=params)
        cards = r.json()["data"]

        await ctx.send(choice(cards)["imageUrl"])


    @commands.command()
    async def lorcana(self, ctx):
        """ Pulls a random Lorcana card """

        url = "https://lorcania.com/api/cardsSearch"
        headers = {"Content-Type": "application/json"}
        data = {"costs": [], "inkwell": [],
            "language": "English", "sorting": "default"}
        r = await self.bot.http_client.post(url, headers=headers, json=data)
        cards = r.json()["cards"]

        await ctx.send(choice(cards)["image"])


    @commands.command()
    async def redemption(self, ctx):
        """ Pulls a random Redemption card """

        # Git tree for cardlist, updated 2023/10/26
        tree = "8e6cf3ed394a99d55c57a9d103fe11afe05dcf54"
        url = ("https://api.github.com/repos/MattJBrinkman/"
            f"RedemptionLackeyCCG/git/trees/{tree}")

        r = await self.bot.http_client.get(url)
        cards = r.json()["tree"]

        cards = [card for card in cards if ".jpg" in card["path"]]
        card = choice(cards)

        r = await self.bot.http_client.get(card["url"])
        img = b64decode(r.json()["content"])
        await ctx.send(file=discord.File(
            fp=BytesIO(img),
            filename=card["path"]))

    @commands.command()
    async def vampire(self, ctx):
        """ Pulls a random Vampire: The Eternal Struggle card """

        # Git tree for cardlist, updated 2023/10/26
        tree = "ea24251f98006109fef961f2ab54cf605aa50cbf"
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
        await ctx.send(file=discord.File(
            fp=BytesIO(img),
            filename=card["path"]))


async def setup(bot):
    await bot.add_cog(Card(bot))