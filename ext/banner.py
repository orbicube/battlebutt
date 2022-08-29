import discord
from discord.ext import tasks, commands
from discord import app_commands
import asyncio

from random import choice
from glob import glob

class Banner(commands.Cog):

    current_banner = ""

    def __init__(self, bot):
        self.bot = bot
        self.banner_task.start()

    def cog_unload(self):
        self.banner_task.stop()

    @tasks.loop(minutes=60.0)
    async def banner_task(self):
        await self.bot.wait_until_ready()

        selected = choice(glob("ext/data/banner/*.jpg"))
        self.current_banner = selected.rsplit('/', 1)[1]


    @app_commands.command()
    async def banner(self, interaction: discord.Interaction):
        """ Posts the filename of the current banner image """

        await interaction.response.send_message(self.current_banner)


async def setup(bot):
    await bot.add_cog(Banner(bot))

async def teardown(bot):
    await bot.remove_cog(Banner)