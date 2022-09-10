import discord
from discord.ext import commands
from discord import app_commands

from typing import Optional

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import json
from random import choice

class Misc(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command()
    async def shadow(self, interaction: discord.Interaction):
        """ Random Shadow the Hedgehog ending name and Sonic song """

        with open('ext/data/shadow.json') as f:
            data = json.load(f)

        title = choice(data['names'])
        song = choice(data['songs'])

        await interaction.response.send_message(f"{title}\n{song}")


    @app_commands.command()
    async def gex(self, interaction: discord.Interaction):
        """ Random Gex quotes """

        with open('ext/data/gex.json') as f:
            data = json.load(f)

        await interaction.response.send_message(
            choice(data['quotes']),
            file=discord.File("ext/data/gex.png"))


    @app_commands.command()
    async def gameawards(self, interaction: discord.Interaction):
        """ Countdown to The Game Awards """

        date = datetime(2022, 12, 9, 1, 0, 0, tzinfo=timezone.utc)

        if discord.utils.utcnow() < date:
            await interaction.response.send_message((
                f"Gamers will unite "
                f"**{discord.utils.format_dt(date, style='R')}**"
                " to celebrate The Game Awards!"))
        else:
            await interaction.response.send_message(
                "gamers have finished uniting and are now in hibernation")


    @app_commands.command()
    @app_commands.describe(video_number="Specific video number")
    async def classicsofgame(self, interaction: discord.Interaction,
        video_number: Optional[int]):
        """ Grab a Classics of Game video """

        with open('ext/data/classicsofgame.json') as f:
            data = json.load(f)

        if video_number:
            try:
                await interaction.response.send_message(
                    data['vids'][video_number-1])
            except IndexError:
                await interaction.response.send_message(
                    "Invalid video number.",
                    ephemeral=True)
        else:
            await interaction.response.send_message(choice(data['vids']))


    @app_commands.command()
    async def beats(self, interaction: discord.Interaction):
        """ Tells the current time in Swatch Internet Time """

        swiss = datetime.now(tz=ZoneInfo("Etc/GMT-1"))
        swatch = round(
            (swiss.second + (swiss.minute * 60) + (swiss.hour * 3600)) / 86.4,
            2)

        if int(swatch) == swatch:
            swatch = int(swatch)

        await interaction.response.send_message(
            f"It is currently **@{swatch}**.")


    @commands.Cog.listener("on_message")
    async def ask8ball(self, message):

        if self.bot.user in message.mentions:
            if message.content.endswith("?"):
                with open ("ext/data/8ball.json") as f:
                    await message.reply(choice(json.load(f)['responses']))


    @commands.Cog.listener("on_message")
    async def witchmercy(self, message):

        match = ["witch mercy", "witchmercy", "which mercy"]
        if any(x in message.content for x in match):
            await message.add_reaction(
                "<:witchmercydonottouch:809289934182678539>")


async def setup(bot):
    await bot.add_cog(Misc(bot))