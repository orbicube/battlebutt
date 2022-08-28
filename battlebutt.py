import discord
from discord import app_commands
from discord.ext import commands

import asyncio
import re
import json

from credentials import DISCORD_TOKEN

extensions = [
    'ext.admin',
    'ext.card',
    'ext.misc'
]

intents = discord.Intents.default()
intents.message_content = True

discord.utils.setup_logging()

bot = commands.Bot(command_prefix=commands.when_mentioned_or(), intents=intents)

async def main():
    async with bot:
        for ext in extensions:
            await bot.load_extension(ext)
        await bot.start(DISCORD_TOKEN)

asyncio.run(main())
