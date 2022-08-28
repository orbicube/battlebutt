import discord
from discord import app_commands
from discord.ext import commands

from typing import Optional

import httpx


class Card(commands.GroupCog, name="card"):

    def __init__(self, bot):
        self.bot = bot
        super().__init__()

    @app_commands.command()
    @app_commands.describe(reason="reason you're pulling the card")
    async def yugioh(self, interaction: discord.Interaction, reason: Optional[str]):
        """ Pulls a random Yu-Gi-Oh! card. """
        # Get random card
        url = "https://db.ygoprodeck.com/api/v7/randomcard.php"
        async with httpx.AsyncClient() as client:
            r = await client.get(url)
            card = r.json()

        await interaction.response.send_message(
            card['card_images'][0]['image_url'])

async def setup(bot):
    await bot.add_cog(Card(bot))