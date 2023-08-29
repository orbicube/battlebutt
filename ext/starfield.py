import discord
from discord.ext import commands
from discord import app_commands

from datetime import datetime, timezone
import aiosqlite

class Starfield(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command()
    @app_commands.describe(guess="Your estimation of the Metacritic score.")
    async def starfield(self, interaction: discord.Interaction,
        guess: app_commands.Range[int, 1, 100] = 80):
        """ Guess the Starfield metascore """

        # Check for cutoff date
        embargo = datetime(2023, 8, 31, 15, 55, 0, tzinfo=timezone.utc)
        if discord.utils.utcnow() > embargo:
            await interaction.response.send_message(
                "Predictions are closed.", ephemeral=True)
            return

        # Grab existing guess
        async with aiosqlite.connect("ext/data/starfield.db") as db:
            async with db.execute("""SELECT guess FROM starfield
                WHERE user_id=?""", (interaction.user.id,)) as cursor:
                saved_guess = await cursor.fetchone()

            if not saved_guess:
                await db.execute("INSERT INTO starfield VALUES (?, ?)",
                    (interaction.user.id, interaction.user.name, guess))
                await db.commit()
                await interaction.response.send_message(
                    f"Guess saved as *{guess}*.")
            elif saved_guess[0] == guess:
                await interaction.response.send_message(
                    "That's already your guess.", ephemeral=True)
            else:
                await db.execute("""UPDATE starfield SET guess=?
                    WHERE user_id=?""", (guess, interaction.user.id))
                await db.commit()
                await interaction.response.send_message(
                    f"Guess changed from *{saved_guess[0]}* to *{guess}*.")


async def setup(bot):
    async with aiosqlite.connect("ext/data/starfield.db") as db:
        await db.execute("""CREATE TABLE IF NOT EXISTS starfield
            (user_id integer PRIMARY KEY, username text, guess integer)""")
        await db.commit()

    await bot.add_cog(Starfield(bot))

async def teardown(bot):
    await bot.remove_cog(Starfield)