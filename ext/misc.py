import discord
from discord.ext import commands
from discord import app_commands

from typing import Optional

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

class Misc(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command()
    async def beats(self, interaction: discord.Interaction):
        """ Tells the current time in Swatch Internet Time. """
        swiss = datetime.now(tz=ZoneInfo("Etc/GMT-1"))

        swatch = round(
            (swiss.second + (swiss.minute * 60) + (swiss.hour * 3600)) / 86.4,
            2)

        if int(swatch) == swatch:
            swatch = int(swatch)

        await interaction.response.send_message(
            f"It is currently **@{swatch}**.")


async def setup(bot):
    await bot.add_cog(Misc(bot))