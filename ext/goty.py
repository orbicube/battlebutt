import discord
from discord import app_commands
from discord.ext import commands

import aiosqlite
import time
from datetime import datetime, timezone
from typing import Optional, Literal
from random import sample, shuffle

from ext.util.twitchauth import twitch_auth

from credentials import TWITCH_ID, TWITCH_SECRET, ERROR_CHANNEL

class Goty(commands.Cog):

    igdb_params = "sort rating_count desc; limit 25; fields name;"
    pos_enum = {
        "first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5,
        "sixth": 6, "seventh": 7, "eighth": 8, "ninth": 9, "tenth": 10 
    }

    def __init__(self, bot):
        self.bot = bot

    @app_commands.describe(
        first="Your #1 game of 2024", second="Your #2 game of 2024",
        third="Your #3 game of 2024", fourth="Your #4 game of 2024",
        fifth="Your #5 game of 2024", sixth="Your #6 game of 2024",
        seventh="Your #7 game of 2024", eighth="Your #8 game of 2024",
        ninth="Your #9 game of 2024", tenth="Your #10 game of 2024")
    @app_commands.command()
    async def goty(self, interaction: discord.Interaction,
        first: Optional[str] = None, second: Optional[str] = None,
        third: Optional[str] = None, fourth: Optional[str] = None,
        fifth: Optional[str] = None, sixth: Optional[str] = None,
        seventh: Optional[str] = None, eighth: Optional[str] = None,
        ninth: Optional[str] = None, tenth: Optional[str] = None
    ):
        # Set existing games to null in case incomplete list
        await self.bot.db.execute("""
            UPDATE goty2024 SET game = NULL
            WHERE user_id = $1""",
            interaction.user.id)

        # Iterate through all parameters, inserting/updating
        for param in interaction.data.get("options", []):
            await self.bot.db.execute("""INSERT INTO goty2024
                VALUES ($1, $2, $3)
                ON CONFLICT(user_id, position) DO UPDATE
                SET game = EXCLUDED.game""",
                interaction.user.id,
                self.pos_enum[param["name"]],
                param["value"])

        await interaction.response.send_message(
            "List submitted!", ephemeral=True)

    
    @goty.autocomplete('first')
    @goty.autocomplete('second')
    @goty.autocomplete('third')
    @goty.autocomplete('fourth')
    @goty.autocomplete('fifth')
    @goty.autocomplete('sixth')
    @goty.autocomplete('seventh')
    @goty.autocomplete('eighth')
    @goty.autocomplete('ninth')
    @goty.autocomplete('tenth')
    async def goty_autocomplete(self,
        interaction: discord.Interaction,
        current: str,) -> list[app_commands.Choice[str]]:

        completes = []
        if current:
            # Search IGDB for parameter input
            headers = await twitch_auth(self.bot.db, self.bot.http_client)
            headers["Content-Type"] = "text/plain"

            r = await self.bot.http_client.post(
                "https://api.igdb.com/v4/games/",
                headers=headers,
                data=f'where name ~ *"{current}"*; {self.igdb_params}')
            games = r.json()
            completes = [app_commands.Choice(
                name=game['name'], value=game['name'])
                for game in games]
        else:
            # If no input yet, try and get existing submission for parameter
            for opt in interaction.data.get("options", []):
                if opt.get("focused", False):
                    position = self.pos_enum[opt["name"]]

            game = await self.bot.db.fetchrow(
                """SELECT game FROM goty2024
                WHERE user_id=$1 AND position=$2""",
                interaction.user.id, position)

            if game:
                completes = [app_commands.Choice(name=game[0], value=game[0])]
            else:
                # If new submission, get random sample of games from DB
                games = await self.bot.db.fetch(
                    "SELECT DISTINCT game from goty2024")
                if len(games) < 25:
                    shuffle(games)
                else:
                    games = sample(games, 25)
                completes = [app_commands.Choice(
                    name=game[0], value=game[0]) for game in games]

        return completes


async def setup(bot):
    await bot.db.execute("""CREATE TABLE IF NOT EXISTS goty2024
        (user_id bigint, position integer, game text,
        UNIQUE(user_id, position))""")

    await bot.add_cog(Goty(bot))