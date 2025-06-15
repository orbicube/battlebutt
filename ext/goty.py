import discord
from discord import app_commands
from discord.ext import commands

import aiosqlite
import time
from datetime import datetime, timezone
from typing import Optional, Literal
from random import sample, shuffle

from ext.util.twitchauth import twitch_auth
from credentials import TWITCH_ID, TWITCH_SECRET, GOTY_KEY

disp_year = {
    1: "2010s"
}

class GotyShareButton(discord.ui.Button):
    def __init__(self, msg):
        self.msg = msg

        super().__init__(
            style=discord.ButtonStyle.primary, label='Share')

    async def callback(self, interaction: discord.Interaction):
        self.msg = f"{self.msg}\n-# Shared by {interaction.user.mention}"
        await interaction.response.send_message(self.msg,
            allowed_mentions=discord.AllowedMentions(users=False))

class ResultsYearDropdown(discord.ui.Select):
    def __init__(self, db, options):
        self.db = db

        super().__init__(placeholder="Pick a year to view GotY results:",
            min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        year = int(self.values[0])
        top_games = await self.db.fetch(
            """SELECT game, score FROM goty_results
            WHERE year=$1 AND guild_id=$2 ORDER BY score DESC LIMIT 20""",
            year, interaction.guild_id)

        msg = [f"## Game of the {'Decade' if year < 1950 else 'Year'}"]
        msg[0] += f" - {disp_year.get(year, year)}"
        prev_rank, prev_result = 0, 0
        ranks = []
        for index, game in enumerate(top_games, start=1):
            if index == 1:
                rank = index
                prev_rank = index
                prev_result = game[1]
            else:
                if game[1] == prev_result:
                    rank = prev_rank
                else:
                    rank = index
                    prev_rank = index
                    prev_result = game[1]
            msg.append((
                f"{rank}\u200d. **{game[0]}** ({game[1]} points)"))
        msg = "\n".join(msg)

        # Check for existing button, replace if so otherwise make new
        view_button = next((
            x for x in self.view.children
            if x.__class__.__name__ == "GotyShareButton"),
            None)
        if view_button:
            view_button.msg = msg
        else:
            self.view.add_item(GotyShareButton(msg))

        await interaction.response.edit_message(
            content=msg, view=self.view)

class ResultsView(discord.ui.View):
    def __init__(self, db, options):
        super().__init__()

        self.add_item(ResultsYearDropdown(db, options))


class UserYearDropdown(discord.ui.Select):
    def __init__(self, db, options, user):
        self.db = db
        self.user = user

        super().__init__(
            placeholder=f"Pick a year to view {user.display_name}'s GotY list:",
            min_values=1, max_values=1, options=options)

    async def callback(self, interaction:discord.Interaction):
        year = int(self.values[0])
        user_list = await self.db.fetch(
            """SELECT game, position FROM goty
            WHERE user_id=$1 AND year=$2 AND guild_id=$3 AND game IS NOT NULL
            ORDER BY position ASC""",
            self.user.id, year, interaction.guild_id)

        msg = [f"## {self.user.display_name}'s Top Games of "]
        msg[0] += f"{'the ' if year < 1950 else ''}{disp_year.get(year, year)}"
        for game in user_list:
            msg.append((
                f"1. **{game[0]}**"))
        msg = "\n".join(msg)

        # Check for existing button, replace if so otherwise make new
        view_button = next((
            x for x in self.view.children
            if x.__class__.__name__ == "GotyShareButton"),
            None)
        if view_button:
            view_button.msg = msg
        else:
            self.view.add_item(GotyShareButton(msg))
        await interaction.response.edit_message(
            content=msg, view=self.view)

class UserYearView(discord.ui.View):
    def __init__(self, db, options, user):
        super().__init__()

        self.add_item(UserYearDropdown(db, options, user))


class Goty(commands.GroupCog):

    igdb_params = "sort rating_count desc; limit 25; fields name;"
    pos_enum = {
        "first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5,
        "sixth": 6, "seventh": 7, "eighth": 8, "ninth": 9, "tenth": 10 
    }
    year = 2015
    closing_date = datetime(2025, 8, 1, 8, 0, 0, tzinfo=timezone.utc)

    def __init__(self, bot):
        self.bot = bot
        self.user_ctx = app_commands.ContextMenu(
            name="View GotY Lists",
            callback=self.user_list)
        self.bot.tree.add_command(self.user_ctx)

    async def cog_unload(self):
        self.bot.tree.remove_command(
            self.user_ctx.name,
            type=self.user_ctx.type)

    def voting_open(self):
        return discord.utils.utcnow() < self.closing_date

    @app_commands.describe(
        first=f"Your #1 game of {year}", second=f"Your #2 game of {year}",
        third=f"Your #3 game of {year}", fourth=f"Your #4 game of {year}",
        fifth=f"Your #5 game of {year}", sixth=f"Your #6 game of {year}",
        seventh=f"Your #7 game of {year}", eighth=f"Your #8 game of {year}",
        ninth=f"Your #9 game of {year}", tenth=f"Your #10 game of {year}")
    @app_commands.command(description=f"Vote for your favourite game of {year}")
    async def vote(self, interaction: discord.Interaction,
        first: Optional[str] = None, second: Optional[str] = None,
        third: Optional[str] = None, fourth: Optional[str] = None,
        fifth: Optional[str] = None, sixth: Optional[str] = None,
        seventh: Optional[str] = None, eighth: Optional[str] = None,
        ninth: Optional[str] = None, tenth: Optional[str] = None
    ):
        if not self.voting_open():
            await interaction.response.send_message(
                "Voting has closed.", ephemeral=True)
            return

        url_params = {
            "key": GOTY_KEY,
            "id": interaction.user.id,
            "name": interaction.user.global_name
        }

        # Format parameters for db entry as tuple
        submissions = []
        games = {}
        for param in interaction.data["options"][0]["options"]:
            pos_int = self.pos_enum[param["name"]]
            submissions.append((
                interaction.user.id, interaction.guild_id,
                self.year, pos_int, param["value"]))

            url_params[f"g{pos_int}"] = param["value"]

            # Check for dupes
            games[param["value"]] = 1
        if len([*games]) < len(submissions):
            await interaction.response.send_message(
                "You can't submit duplicate games.",
                ephemeral=True)
            return

        if not submissions:
            await interaction.response.send_message(
                "You have to input at least one game.",
                ephemeral=True)
            return

        # Set existing games to null in case incomplete list
        await self.bot.db.execute("""
            UPDATE goty SET game = NULL
            WHERE user_id=$1 AND guild_id=$2 AND year=$3""",
            interaction.user.id, interaction.guild_id, self.year)

        await self.bot.db.executemany("""INSERT INTO goty
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT(user_id, guild_id, year, position) DO UPDATE
            SET game = EXCLUDED.game""",
            submissions)

        await self.tabulate(interaction.guild_id, self.year)

        # If modern list, send to website
        curr_year = discord.utils.utcnow().year
        if self.year == curr_year or (self.year+1) == curr_year:
            await self.bot.http_client.get(
                f"https://goty.orb.party/{self.year}/discimport/",
                params=url_params)

        await interaction.response.send_message(
            "List submitted!", ephemeral=True)

    @vote.autocomplete('first')
    @vote.autocomplete('second')
    @vote.autocomplete('third')
    @vote.autocomplete('fourth')
    @vote.autocomplete('fifth')
    @vote.autocomplete('sixth')
    @vote.autocomplete('seventh')
    @vote.autocomplete('eighth')
    @vote.autocomplete('ninth')
    @vote.autocomplete('tenth')
    async def vote_autocomplete(self,
        interaction: discord.Interaction,
        current: str,) -> list[app_commands.Choice[str]]:

        completes = []
        if current:
            # Format query based on whether current or retro GotY
            q_str = f'where name ~ *"{current}"*'
            if self.year < self.closing_date.year-1:
                q_str = f'{q_str} & release_dates.y = {self.year}'
            q_str += ';'

            # Search IGDB for parameter input
            headers = await twitch_auth(self.bot.db, self.bot.http_client)
            headers["Content-Type"] = "text/plain"
            r = await self.bot.http_client.post(
                "https://api.igdb.com/v4/games/",
                headers=headers,
                data=f'{q_str} {self.igdb_params}')
            games = r.json()

            completes = [app_commands.Choice(
                name=game['name'], value=game['name'])
                for game in games]
        else:
            # If no input yet, try and get existing submission for parameter
            for opt in interaction.data["options"][0]["options"]:
                if opt.get("focused", False):
                    position = self.pos_enum[opt["name"]]

            game = await self.bot.db.fetchrow(
                """SELECT game FROM goty
                WHERE user_id=$1 AND guild_id=$2 AND year=$3 AND position=$4""",
                interaction.user.id, interaction.guild_id, self.year, position)

            if game:
                completes = [app_commands.Choice(name=game[0], value=game[0])]
            else:
                # If new submission, get random sample of games from DB
                games = await self.bot.db.fetch(
                    """SELECT DISTINCT game FROM goty
                    WHERE year = $1 AND guild_id=$2""",
                    self.year, interaction.guild_id)
                if len(games) < 25:
                    shuffle(games)
                else:
                    games = sample(games, 25)
                completes = [app_commands.Choice(
                    name=game[0], value=game[0]) for game in games]

        return completes


    @app_commands.command()
    async def results(self, interaction: discord.Interaction):
        """View the server's top ten games of each year """
        years = await self.bot.db.fetch(
            """SELECT DISTINCT year FROM goty_results
            WHERE guild_id=$1 ORDER BY year DESC""",
            interaction.guild_id)

        options = []
        for year in years:
            if year[0] != self.year or not self.voting_open():
                options.append(discord.SelectOption(
                    label=disp_year.get(year[0], year[0]), value=year[0]))

        if not options:
            await interaction.response.send_message(
                "This server doesn't have any previous GotY lists.",
                ephemeral=True)
            return

        view = ResultsView(self.bot.db, options)

        await interaction.response.send_message(view=view, ephemeral=True)


    async def user_list(self, 
        interaction: discord.Interaction, user: discord.User):
        years = await self.bot.db.fetch(
            """SELECT DISTINCT year FROM goty
            WHERE user_id=$1 AND guild_id=$2 ORDER BY year DESC""",
            user.id, interaction.guild_id)

        options = []
        for year in years:
            options.append(discord.SelectOption(
                label=disp_year.get(year[0], year[0]), value=year[0]))

        if not options:
            await interaction.response.send_message(
                f"{user.display_name} doesn't have any submitted lists.",
                ephemeral=True)
            return

        view = UserYearView(self.bot.db, options, user)

        await interaction.response.send_message("", view=view, ephemeral=True)


    async def tabulate(self, guild: int, year: int):
        # Clear previous results in case games change
        await self.bot.db.execute("""DELETE FROM goty_results 
            WHERE year=$1 AND guild_id=$2""", year, guild)

        votes = await self.bot.db.fetch("""SELECT game, position FROM goty
            WHERE year=$1 AND guild_id=$2 AND game IS NOT NULL""", year, guild)
        
        games = {}
        for v in votes:
            if v["game"] in games.keys():
                games[v["game"]] += (11 - v["position"])
            else:
                games[v["game"]] = (11 - v["position"])
        
        await self.bot.db.executemany(
            "INSERT INTO goty_results VALUES ($1, $2, $3, $4)",
            [(k, guild, year, v) for k, v in games.items()])


async def setup(bot):
    await bot.db.execute("""CREATE TABLE IF NOT EXISTS goty
        (user_id bigint, guild_id bigint, year integer, position integer, 
        game text, UNIQUE(user_id, guild_id, year, position))""")
    await bot.db.execute("""CREATE TABLE IF NOT EXISTS goty_results
        (game text, guild_id bigint, year integer, score integer,
        UNIQUE(game, guild_id, year))""")

    await bot.add_cog(Goty(bot))

async def teardown(bot):
    await bot.remove_cog(Goty)