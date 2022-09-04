import discord
from discord.ext import tasks, commands
from discord import app_commands
import asyncio

from random import choice
from pathlib import Path

class Banner(commands.Cog):

    current_banner = ""
    banner_guilds = [
        122087203760242692
    ]

    def __init__(self, bot):
        self.bot = bot
        self.banner_task.start()

    def cog_unload(self):
        self.banner_task.stop()

    @tasks.loop(minutes=60.0)
    async def banner_task(self):
        await self.bot.wait_until_ready()

        selected = choice(list(Path("ext/data/banner").glob("*.jpg")))

        self.current_banner = selected.name

        with open(selected, 'rb') as f:
            for guild in self.banner_guilds:
                try:
                    await self.bot.get_guild(guild).edit(banner=f.read())
                except Exception as e:
                    print(f"Failed to change guild {guild}'s banner: {e}")
                    pass


    @app_commands.command()
    async def petz(self, interaction: discord.Interaction):
        """ Posts the filename of the current banner image """

        await interaction.response.send_message(self.current_banner)


async def setup(bot):
    await bot.add_cog(Banner(bot))

async def teardown(bot):
    await bot.remove_cog(Banner)