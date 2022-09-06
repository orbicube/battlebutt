import discord
from discord.ext import commands, tasks
from discord import app_commands

from random import randint
from datetime import datetime
from zoneinfo import ZoneInfo
import aiosqlite

from credentials import GIANT_BOMB_KEY, DEBUG_CHANNEL

class GiantBomb(commands.Cog):

    gb_logo = "https://ptpimg.me/lahhsn.png"
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
        self.check_upcoming.start()
        self.check_videos.start()

    def cog_unload(self):
        self.update_game.cancel()
        self.check_upcoming.cancel()
        self.check_videos.cancel()

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

        # Snuff out current presence to avoid issues
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


    @app_commands.command()
    async def playing(self, interaction: discord.Interaction):
        """ Post the bot's currently playing game """

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

        await interaction.response.send_message(embed=embed)

        # Insert URL into database as if the user posted it.
        abe_msg = await interaction.original_response()
        abe_msg.content = game["url"]
        abe_msg.author = interaction.user
        await self.bot.get_cog("Abe").check_abes(abe_msg)


    @tasks.loop(minutes=1.0)
    async def check_videos(self):
        await self.bot.wait_until_ready()

        params = {
            "api_key": GIANT_BOMB_KEY,
            "limit": "10",
            "field_list":"deck,id,name,length_seconds," \
                "site_detail_url,image",
            "filter": "premium:false",
            "format": "json"
        }

        r = await self.bot.http_client.get(
            "https://www.giantbomb.com/api/videos/",
            headers=self.headers, params=params)
        results = r.json()["results"]

        for video in results:
            # Check if video is in the database
            async with aiosqlite.connect("ext/data/giantbomb.db") as db:
                async with db.execute(""" SELECT video_id FROM video_history 
                    WHERE video_id=?""", (video["id"], )) as cursor:
                    video_exists = await cursor.fetchone()

                if not video_exists:
                    embed = discord.Embed(
                        title=video["name"],
                        description=video["deck"],
                        url=video["site_detail_url"],
                        color=15474724)

                    embed.set_image(url=video["image"]["original_url"])

                    embed.set_author(
                        name="New Giant Bomb Video",
                        icon_url=self.gb_logo)

                    # Rarely videos don't have attached lengths
                    if video["length_seconds"] > 0:
                        # Format video length in "?h ?m ?s" format
                        minutes, seconds = divmod(video["length_seconds"], 60)
                        hours, minutes = divmod(minutes, 60)

                        embed.set_footer(text=(
                            f"{f'{hours}h ' if hours else ''}"
                            f"{f'{minutes}m ' if minutes else ''}"
                            f"{f'{seconds}s ' if seconds else ''}"))

                    for c in self.post_channels:
                        await self.bot.get_channel(c).send(embed=embed)

                    await db.execute(""" INSERT INTO video_history
                        VALUES (?)""", (video["id"], ))
                    await db.commit()


    @tasks.loop(minutes=1.0)
    async def check_upcoming(self):
        await self.bot.wait_until_ready()

        r = await self.bot.http_client.get(
            "https://www.giantbomb.com/upcoming_json",
            headers=self.headers)
        upcoming = r.json()['upcoming']

        async with aiosqlite.connect("ext/data/giantbomb.db") as db:
            # Because this is a live updating list
            # we grab all entries then clear the table
            async with db.execute(""" SELECT upcoming_name 
                FROM upcoming """) as cursor:
                upcoming_list = await cursor.fetchall()
                upcoming_list = [up[0] for up in upcoming_list]

            await db.execute("DELETE FROM upcoming")
            await db.commit()

            for up in upcoming:
                if (up["title"] not in upcoming_list and 
                    "Community Spotlight" not in up["title"]):
                    
                    post_date = datetime.strptime(
                        up["date"], "%b %d, %Y %I:%M %p")
                    post_date = post_date.replace(
                        tzinfo=ZoneInfo("America/Los_Angeles"))
                    post_str = discord.utils.format_dt(post_date, style="R")
                    
                    embed = discord.Embed(
                        title=up["title"],
                        description=f"Coming up {post_str}.",
                        color=15474724)
                    embed.set_author(name="Upcoming on Giant Bomb",
                        icon_url=self.gb_logo)

                    if up["image"]:
                        embed.set_image(url=f"https://{up['image']}")

                    for c in self.post_channels:
                        await self.bot.get_channel(c).send(embed=embed)

                await db.execute(""" INSERT INTO upcoming 
                    VALUES (?)""", (up["title"], ))
                await db.commit()


async def setup(bot):
    async with aiosqlite.connect("ext/data/giantbomb.db") as db:
        await db.execute("""CREATE TABLE IF NOT EXISTS video_history
            (video_id integer, UNIQUE(video_id))""")
        await db.execute("""CREATE TABLE IF NOT EXISTS upcoming
            (upcoming_name text)""")
        await db.commit()

    await bot.add_cog(GiantBomb(bot))

async def teardown(bot):
    await bot.remove_cog(GiantBomb)