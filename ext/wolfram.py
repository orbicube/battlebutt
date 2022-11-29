import discord
from discord import app_commands
from discord.ext import commands

from credentials import WOLFRAM_KEY

class Wolfram(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command()
    @app_commands.describe(query="What you want to ask")
    async def query(self, interaction: discord.Interaction, query: str):
        """ Send a query to Wolfram Alpha """

        params = {
            "appid": WOLFRAM_KEY,
            "i": query
        }
        r = await self.bot.http_client.get(
            "https://api.wolframalpha.com/v1/spoken",
            params=params)

        await interaction.response.send_message(f"{r.text}.",
            ephemeral=(r.status_code == 501))


async def setup(bot):
    await bot.add_cog(Wolfram(bot))