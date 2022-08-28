import discord
from discord import app_commands
from discord.ext import commands

from typing import Optional
from random import choice, randint

import httpx
from lxml import html
from PIL import Image
from io import BytesIO

class Card(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command()
    @commands.cooldown(rate=1, per=60.0, type=commands.BucketType.user)
    @app_commands.describe(game="TCG you want to pull a card from.")
    async def card(self, ctx, game: Optional[str] = None):
        """ Pulls a random TCG card. """

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
            'cardfightvanguard']

        return [app_commands.Choice(name=game, value=game)
            for game in games if current.lower() in game.lower() ] 


    @commands.command(aliases=['poke'])
    @commands.cooldown(rate=1, per=60.0, type=commands.BucketType.user)
    async def pokemon(self, ctx):
        """ Posts a random Pokemon TCG card. """

        url = "https://pkmncards.com/?random"
        async with httpx.AsyncClient(http2=True) as client:
            r = await client.get(url, follow_redirects=True)

        # Scrape image from page metadata
        page = html.fromstring(r.text)
        image_url = page.xpath("//meta[@property='og:image']/@content")[0]
        image_url = image_url.split('?')[0]

        await ctx.send(image_url)


    @commands.command(aliases=['ygo'])
    @commands.cooldown(rate=1, per=60.0, type=commands.BucketType.user)
    async def yugioh(self, ctx):
        """ Pulls a random Yu-Gi-Oh! card. """
       
        url = "https://db.ygoprodeck.com/api/v7/randomcard.php"
        async with httpx.AsyncClient() as client:
            r = await client.get(url)
            card = r.json()

        await ctx.send(card['card_images'][0]['image_url'])


    @commands.command()
    @commands.cooldown(rate=1, per=60.0, type=commands.BucketType.user)
    async def digimon(self, ctx):
        """ Posts a random Digimon card. """

        url = "https://digimoncard.io/api-public/getAllCards.php?series=Digimon%20Card%20Game"
        async with httpx.AsyncClient() as client:
            r = await client.get(url)
            card_list = r.json()

        await ctx.send(
            f"https://images.digimoncard.io/images/cards/{choice(card_list)['cardnumber']}.jpg")


    @commands.command(aliases=['magic'])
    @commands.cooldown(rate=1, per=60.0, type=commands.BucketType.user)
    async def mtg(self, ctx):
        """ Pulls a random Magic the Gathering card. """

        url = "https://api.scryfall.com/cards/random"
        async with httpx.AsyncClient() as client:
            r = await client.get(url)
            card = r.json()

        # If it doesn't have an image then try again
        if card['image_status'] == 'missing' or card['image_status'] == 'placeholder':
            await self.mtg(ctx)
        else:
            # If card has two sides, pick one side
            if not "image_uris" in card and "card_faces" in card:
                card['image_uris'] = card['card_faces'][randint(0,1)]['image_uris']
            
            await ctx.send(card['image_uris']['border_crop'])


    @commands.command(aliases=['fab'])
    @commands.cooldown(rate=1, per=60.0, type=commands.BucketType.user)
    async def fleshandblood(self, ctx):
        """ Posts a random Flesh and Blood card. """

        url = "https://api.fabdb.net/cards"
        async with httpx.AsyncClient() as client:
            r = await client.get(url)
            page = r.json()

        # Pick random page
        page_select = randint(1, page['meta']['last_page'])        
        params = { "page": page_select }

        # Get random card from random page
        async with httpx.AsyncClient() as client:
            r = await client.get(url, params=params)
            page = r.json()
        card = choice(page['data'])

        await ctx.send(card['image'].split('?')[0])


    @commands.command()
    @commands.cooldown(rate=1, per=60.0, type=commands.BucketType.user)
    async def gateruler(self, ctx):
        """ Posts a random Gate Ruler card. """

        # Defer in case edit takes too long
        await ctx.defer()

        # Get max page number
        url = "https://www.gateruler-official.com/card_search"
        async with httpx.AsyncClient() as client:
            r = await client.get(url)   
            page = html.fromstring(r.text)

            max_pages = page.xpath("//ul[@class='pagination']/li/a/text()")[-2]

            # Pick random page
            params = { "page": randint(1, int(max_pages)) }
            
            r = await client.get(url, params=params)
            page = html.fromstring(r.text)

            # Get random card       
            cards = page.xpath("//li[@class='com_btm']/a/img/@src")
            card_url = choice(cards)

            r = await client.get(card_url)

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
    @commands.cooldown(rate=1, per=60.0, type=commands.BucketType.user)
    async def finalfantasy(self, ctx):
        """ Posts a random Final Fantasy TCG card. """

        # Defer in case JSON download takes too long
        await ctx.defer()

        url = "https://fftcg.square-enix-games.com/na/get-cards"
        async with httpx.AsyncClient() as client:
            r = await client.get(url)           
            cards = r.json()

        card = choice(cards['cards'])
        if '\/' in card['Code']:
            card['Code'] = card['Code'].split('\/')[0]

        await ctx.send(
            f"https://fftcg.cdn.sewest.net/images/cards/full/{card['Code']}_eg.jpg")


    @commands.command(aliases=["cfv", "cfvangaurd"])
    @commands.cooldown(rate=1, per=60.0, type=commands.BucketType.user)
    async def cardfightvanguard(self, ctx):
        """ Posts a random Cardfight!! Vanguard card. """

        # Defer in case multiple requests take too long
        await ctx.defer()

        # Get first page to figure out max page
        url = "https://en.cf-vanguard.com/cardlist/cardsearch"
        async with httpx.AsyncClient() as client:
            r = await client.get(url)
            page = html.fromstring(r.text)

            # 24 cards per page
            card_count = page.xpath("//div[@class='number']/text()")[0]
            card_count = int(card_count[:-8])
            params = {
                "page": randint(1, int((card_count / 24) + 1))
            }

            # Get page with cards to pick
            r = await client.get(url, params=params)
            page = html.fromstring(r.text)

        # Pick card
        card = "https://en.cf-vanguard.com{}".format(
            choice(page.xpath("//img[@class='object-fit-img']/@src")))
        await ctx.send(card)


async def setup(bot):
    await bot.add_cog(Card(bot))