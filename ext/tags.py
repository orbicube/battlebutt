import discord
from discord.ext import commands
from discord import app_commands

import json

class Tags(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command()
    async def tags(self, interaction: discord.Interaction):
        """ List current tags (mini commands that return static text) """
        with open("ext/data/tags.json") as f:
            tags = json.load(f)

        await interaction.response.send_message(
            ", ".join(sorted(tags.keys())),
            ephemeral=True)


    @commands.Cog.listener("on_message")
    async def scan_tags(self, message):

        if self.bot.user in message.mentions:
            with open("ext/data/tags.json") as f:
                tags = json.load(f)
            try:
                await message.reply(tags[message.content.split()[1]])
            except:
                pass


async def setup(bot):
    await bot.add_cog(Tags(bot))
