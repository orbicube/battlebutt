import discord
from discord.ext import commands, tasks
from discord import app_commands

import aiosqlite
from datetime import datetime
import time
from random import randint, choice

import traceback
import sys

from ext.util.twitchauth import twitch_auth
from credentials import TWITCH_ID, TWITCH_SECRET, ERROR_CHANNEL

class IGDB(commands.Cog):

    category_enum = {
        0: "Game",
        1: "DLC",
        2: "Expansion",
        3: "Bundle",
        4: "Standalone Expansion",
        5: "Mod",
        6: "Episode",
        7: "Season",
        8: "Remake",
        9: "Remaster",
        10: "Enhancement",
        11: "Port",
        12: "Source Port",
        13: "Pack/Addon",
        14: "Update"
    }
    plat_alias = {
        "PC (Microsoft Windows)": "PC",
        "Legacy Mobile Device": "Phone",
        "Visual Memory Unit / Visual Memory System": "VMU",
        "Family Computer": "Famicom",
        "PC Engine SuperGrafx": "SuperGrafx",
        "BBC Microcomputer System": "BBC Micro",
        "PC-9800 Series": "PC-98",
        "Family Computer Disk System": "Famicom Disk System",
        "Commodore C64/128/MAX": "Commodore 64",
        "Atari ST/STE": "Atari ST",
        "NEC PC-6000 Series": "PC-60",
        "TRS-80 Color Computer": "TRS-80 CoCo",
        "PC-8800 Series": "PC-88",
        "Handheld Electronic LCD": "Handheld",
        "Web browser": "Browser"
    }
    game_count = 254151
    game = {}
    filter_query = "where themes != (42) & (cover != null | summary != null | first_release_date != null | platforms != null) & game_type != (13);"
    fields_query = "fields name,cover.url,screenshots.url,summary,first_release_date,platforms.name,slug,game_type,parent_game.name,parent_game.platforms.name;"


    def __init__(self, bot):
        self.bot = bot
        self.update_game_count.start()
        self.update_game.start()

    def cog_unload(self):
        self.update_game.cancel()
        self.update_game_count.cancel()


    @app_commands.command()
    async def playing(self, interaction: discord.Interaction):
        """ Post the bot's currently playing game """
        game = self.game

        embed = discord.Embed(
            title=game["name"],
            url=f"https://igdb.com/games/{game['slug']}",
            description=game["summary"] if "summary" in game else "",
            colour=0x9147ff)

        # Set release date if exists
        try:
            embed.timestamp = datetime.fromtimestamp(game["first_release_date"])
        except:
            pass

        # Set cover image if exists
        try:
            embed.set_image(
                url=f"https:{game['cover']['url'].replace('thumb','1080p')}")
        except:
            # Try for screenshots if no box art
            try:
                embed.set_image(
                    url=f"https:{choice(game['screenshots'])['url'].replace('thumb','1080p')}")
            except:
                pass

        inherit_plats = False
        # Highlight that it's a mod and highlight game if not obvious
        if game["game_type"] == 5:
            cat_name = "Mod"
            if game["parent_game"]["name"] not in game["name"]:
                cat_name += f" of {game['parent_game']['name']}"

            embed.set_author(name=cat_name)

        # Inherit parent game for everything except ports/remakes/remasters
        if game["game_type"] and game["game_type"] not in [3, 8, 9, 10, 11]:
            inherit_plats = True

        # Set platforms if exists
        try:
            platforms = [self.plat_alias[x["name"]] if x["name"] in self.plat_alias
                else x["name"] for x in game["platforms"]]
            embed.set_footer(text=", ".join(platforms))
        except:
            if inherit_plats:
                try:
                    platforms = [self.plat_alias[x["name"]] if x["name"] in self.plat_alias
                        else x["name"] for x in game["parent_game"]["platforms"]]
                    embed.set_footer(text=", ".join(platforms))
                except:
                    pass

        await interaction.response.send_message(embed=embed)

        # Insert URL into database as if the user posted it.
        abe_msg = await interaction.original_response()
        abe_msg.content = f"https://igdb.com/games/{game['slug']}"
        abe_msg.author = interaction.user
        await self.bot.get_cog("Abe").check_abes(abe_msg)      


    @tasks.loop(minutes=10.0)
    async def update_game(self):
        await self.bot.wait_until_ready()

        # Setup Twitch API auth
        headers = await twitch_auth(self.bot.db, self.bot.http_client)
        headers['Content-Type']: "text/plain"

        allowed_game = False
        while not allowed_game:
            try: 
                query = f"{self.fields_query} {self.filter_query} limit 1; offset {randint(0, (self.game_count - 1))};"
                r = await self.bot.http_client.post(
                    "https://api.igdb.com/v4/games/",
                    headers=headers,
                    data=query)
                game = r.json()[0]
                if game["category"] != 1 or not ("MP0" in game["name"] or "Tiger" in game["name"]):
                    allowed_game = True
            except Exception as e:
                await self.bot.get_channel(ERROR_CHANNEL).send(
                    f"Error in igdb.update_game(): {type(e)} {e}")
                return          

        self.game = game

        await self.bot.change_presence()
        await self.bot.change_presence(
            activity=discord.Game(name=self.game["name"]))

    @update_game.error
    async def update_game_error(self, error):
        error = getattr(error, 'original', error)

        error_msg = (f"Error in **igdb.update_game()**\n\n"
            f"**Type**: {type(error)}\n\n**Error**: {error}\n\n"
            "**Traceback**:\n```")
        for t in traceback.format_tb(error.__traceback__):
            error_msg += f"{t}\n"
        error_msg += "```"

        await self.bot.get_channel(ERROR_CHANNEL).send(error_msg)
        traceback.print_exception(
            type(error), error, error.__traceback__, file=sys.stderr)


    @tasks.loop(minutes=60.0)
    async def update_game_count(self):

        headers = await twitch_auth(self.bot.db, self.bot.http_client)
        headers["Content-Type"] = "text/plain"

        try:
            r = await self.bot.http_client.post(
                "https://api.igdb.com/v4/games/count",
                headers=headers,
                data=self.filter_query)
            self.game_count = r.json()["count"]
        except Exception as e:
            await self.bot.get_channel(ERROR_CHANNEL).send(
                f"Error in igdb.update_game_count(): {type(e)} {e}")
            return

    @update_game_count.error
    async def update_game_count_error(self, error):
        error = getattr(error, 'original', error)

        error_msg = (f"Error in **igdb.update_game_count()**\n\n"
            f"**Type**: {type(error)}\n\n**Error**: {error}\n\n"
            "**Traceback**:\n```")
        for t in traceback.format_tb(error.__traceback__):
            error_msg += f"{t}\n"
        error_msg += "```"

        await self.bot.get_channel(ERROR_CHANNEL).send(error_msg)
        traceback.print_exception(
            type(error), error, error.__traceback__, file=sys.stderr)


async def setup(bot):
    await bot.add_cog(IGDB(bot))

async def teardown(bot):
    await bot.remove_cog(IGDB)