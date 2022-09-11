import discord
from discord import app_commands
from discord.ext import commands

from typing import Optional
from random import choice, randint

from lxml import html
from PIL import Image
from io import BytesIO

class Card(commands.Cog,
    command_attrs={"cooldown": commands.CooldownMapping.from_cooldown(
        1, 30, commands.BucketType.user)}):

    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command()
    @app_commands.describe(game="TCG you want to pull a card from")
    async def card(self, ctx, game: Optional[str]):
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
        if '\/' in card['Code']:
            card['Code'] = card['Code'].split('\/')[0]

        await ctx.send(("https://fftcg.cdn.sewest.net/images/cards/"
            f"full/{card['Code']}_eg.jpg"))


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


async def setup(bot):
    await bot.add_cog(Card(bot))