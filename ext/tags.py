import discord
from discord.ext import commands, tasks
from discord import app_commands

from typing import Optional

import json
from difflib import get_close_matches
 
class Tags(commands.Cog):

    tags = {}

    def __init__(self, bot):
        self.bot = bot
        self.check_tags.start()

    async def cog_unload(self):
        self.check_tags.cancel()

    @app_commands.command()
    @app_commands.describe(tag="The tag you want the bot to post")
    async def tags(self, interaction: discord.Interaction, tag: Optional[str]):
        """ Posts text matching a given tag, no arguments lists all tags"""

        if not tag:
            await interaction.response.send_message(
                ", ".join(sorted(self.tags.keys())), ephemeral=True)
        else:
            try:
                await interaction.response.send_message(self.tags[tag])
            except:
                await interaction.response.send_message(
                    f"Couldn't find a tag matching `{tag}`.",
                    ephemeral=True)

    @tags.autocomplete('tag')
    async def tag_autocomplete(self, interaction: discord.Interaction,
        current: str,) -> list[app_commands.Choice[str]]:

        return [app_commands.Choice(name=tag, value=tag)
            for tag in self.tags.keys() if current.lower() in tag.lower()]


    @commands.Cog.listener("on_message")
    async def scan_tags(self, message):

        if self.bot.user in message.mentions or message.startswith("/"):
            try:
                await message.channel.send(
                    self.tags[message.content.split()[1]])
            except:
                pass


    @tasks.loop(seconds=60.0)
    async def check_tags(self):

        with open("ext/data/tags.json") as f:
            tags = json.load(f)
        self.tags = tags


async def setup(bot):
    await bot.add_cog(Tags(bot))

async def teardown(bot):
    await bot.remove_cog(Tags)
