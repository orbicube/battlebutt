import discord
from discord import app_commands
from discord.ext import commands
import asyncio

from typing import Optional
from pathlib import Path
import traceback
import sys

import httpx

from credentials import DISCORD_TOKEN, DEBUG_CHANNEL
from translator import ButtTranslator

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

discord.utils.setup_logging()

bot = commands.Bot(command_prefix=commands.when_mentioned_or(), intents=intents)

async def main():
    async with bot:
        await bot.tree.set_translator(ButtTranslator())
        bot.http_client = httpx.AsyncClient(http2=True)

        for file in Path("ext").glob("**/[!_]*.py"):
            ext = ".".join(file.parts).removesuffix(".py")
            try:
                await bot.load_extension(ext)
            except Exception as e:
                print(f"Failed to load extension {ext}: {e}")

        await bot.start(DISCORD_TOKEN)


@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, 
    error: app_commands.AppCommandError):
    error = getattr(error, 'original', error)

    error_msg = (f"Error in **{interaction.command}**\n\n"
        f"**Type**: {type(error)}\n\n**Error**: {error}\n\n**Traceback**:\n```")
    for t in traceback.format_tb(error.__traceback__):
        error_msg += f"{t}\n"
    error_msg += "```"

    if not isinstance(error, commands.CommandOnCooldown):
        await bot.get_channel(DEBUG_CHANNEL).send(error_msg)
        traceback.print_exception(
            type(error), error, error.__traceback__, file=sys.stderr)

    await interaction.response.send_message(f"foo**Error**: {error}",
        ephemeral=True)


@bot.event
async def on_command_error(ctx, error):
    error = getattr(error, 'original', error)

    if isinstance(error, (commands.CommandNotFound, commands.NotOwner)):
        return

    error_msg = (f"Error in **{ctx.command}**\n\n**Type**: {type(error)}\n\n"
        f"**Error**: {error}\n\n**Traceback**:\n```")
    for t in traceback.format_tb(error.__traceback__):
        error_msg += f"{t}\n"
    error_msg += "```"

    if not isinstance(error, commands.CommandOnCooldown):
        await bot.get_channel(DEBUG_CHANNEL).send(error_msg)
        traceback.print_exception(
            type(error), error, error.__traceback__, file=sys.stderr)

    await ctx.reply(f"**Error**: {error}", ephemeral=True)


asyncio.run(main())
