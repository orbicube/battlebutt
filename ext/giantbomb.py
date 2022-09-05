import discord
from discord.ext import commands, tasks
from discord import app_commands

from random import randint
import aiosqlite

from credentials import GIANT_BOMB_KEY, DEBUG_CHANNEL

class GiantBomb(commands.Cog):

    headers = {
        'User-Agent': 'battlebutt/2.0 (github.com/orbicube/battlebutt)',
        'Host': 'www.giantbomb.com'
    }
    post_channels = [
        143562235740946432
    ]
    game_count = 81450
    game = {
    }

    def __init__(self, bot):
        self.bot = bot
        self.update_game.start()

    def cog_unload(self):
        self.update_game.cancel()


    @tasks.loop(minutes=10.0)
    async def update_game(self):
        await self.bot.wait_until_ready()

        params = {
            "api_key": GIANT_BOMB_KEY,
            "limit": "1",
            "offset": randint(0, (self.game_count - 1)),
            "field_list": "api_detail_url",
            "format": "json"
        }

        r = await self.bot.http_client.get(
            "https://www.giantbomb.com/api/games/",
            headers=self.headers, params=params)
        results = r.json()

        # Update max game count
        self.game_count = results["number_of_total_results"]

        # Deletions could happen between updates, making game_count invalid
        if results["number_of_page_results"] == 0:
            self.update_game.restart()

        # You can only get the themes on the /game/ endpoint
        params.pop("limit", None)
        params.pop("offset", None)
        params["field_list"] = ("name,site_detail_url,image,"
            "platforms,deck,themes")
        r = await self.bot.http_client.get(
            results["results"][0]["api_detail_url"],
            headers=self.headers, params=params)
        game = r.json()['results']

        # We use themes to skip adult games
        if "themes" in game.keys():
            if any(theme["name"] == "Adult" for theme in game["themes"]):
                self.update_game.restart()

        # Null out current presence to avoid issues
        await self.bot.change_presence()

        self.game["name"] = game["name"]
        # If game doesn't have its own image, just don't store it
        if "3026329-gb_default-16_9" not in game["image"]["original_url"]:
            self.game["image"] = game["image"]["original_url"]
        else:
            self.game["image"] = ""
        self.game["url"] = game["site_detail_url"]
        self.game["platforms"] = [plat["name"] for plat in game["platforms"]]
        self.game["deck"] = game["deck"]

        await self.bot.change_presence(
            activity=discord.Game(name=game["name"]))

        await self.bot.get_channel(DEBUG_CHANNEL).send(game["name"])


    @app_commands.command()
    async def playing(self, interaction: discord.Interaction):
        """ Post the game that is currently being played by the bot """

        game = self.game

        embed = discord.Embed(
            title=game["name"],
            url=game["url"],
            description=game["deck"] if game["deck"] else "")

        if game["image"]:
            embed.set_image(url=game["image"])

        if game["platforms"]:
            if len(game["platforms"]) > 1:
                plat_format = ", ".join(game["platforms"][:-1])
                plat_format += f" and {game['platforms'][-1]}"
            else:
                plat_format = game["platforms"][0]

            embed.set_footer(text=plat_format)

        await interaction.response.send_message(
            game["url"], embed=embed)

        # Insert URL into database as if the user posted it.
        abe_msg = await interaction.original_response()
        abe_msg.content = game["url"]
        abe_msg.author = interaction.user
        await self.bot.get_cog("Abe").check_abes(abe_msg)


async def setup(bot):
    await bot.add_cog(GiantBomb(bot))

async def teardown(bot):
    await bot.remove_cog(GiantBomb)