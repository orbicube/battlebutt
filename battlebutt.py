import discord
from discord import app_commands
from discord.ext import commands

from typing import Optional
import asyncio

import httpx

from credentials import DISCORD_TOKEN
from translator import ButtTranslator

extensions = [
    'ext.admin',
    'ext.card',
    'ext.misc',
    'ext.roles',
    'ext.mfw',
    'ext.banner',
    'ext.funko',
    'ext.archive'
]

intents = discord.Intents.default()
intents.message_content = True

discord.utils.setup_logging()

bot = commands.Bot(command_prefix=commands.when_mentioned_or(), intents=intents)

async def main():
    async with bot:
        await bot.tree.set_translator(ButtTranslator())
        bot.http_client = httpx.AsyncClient(http2=True)
        for ext in extensions:
            await bot.load_extension(ext)
        await bot.start(DISCORD_TOKEN)

asyncio.run(main())
