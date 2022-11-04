import discord
from discord.ext import commands
from discord import app_commands

from base64 import b64decode
from io import BytesIO

from credentials import OPENAI_KEY

class OpenAI(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @app_commands.checks.cooldown(1, 600)
    @app_commands.describe(prompt="Prompt used to generate the image")
    @app_commands.command()
    async def generate(self, interaction: discord.Interaction, prompt: str):
        """ Generate and post a DALL-E image """

        allowed_channels = {
            122087203760242692: 991994435191722004,
            143562235740946432: 674578028579258378
        }

        try:
            if interaction.channel.id != allowed_channels[interaction.guild.id]:
                await interaction.response.send_message(
                    f"This is not a valid channel, try <#{allowed_channels[interaction.guild.id]}>.",
                    ephemeral=True)
                return
        except:
            pass


        url = "https://api.openai.com/v1/images/generations"
        data = {
            "prompt": prompt,
            "size": "512x512",
            "response_format": "b64_json",
            "user": f"discord-{interaction.user.id}"
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {OPENAI_KEY}"
        }

        await interaction.response.defer()

        r = await self.bot.http_client.post(
            url, headers=headers, json=data, timeout=30.0)
        response = r.json()

        image = BytesIO(b64decode(response['data'][0]['b64_json']))

        await interaction.followup.send(
            file=discord.File(image, filename=f"{interaction.id}.png"))


async def setup(bot):
    await bot.add_cog(OpenAI(bot))