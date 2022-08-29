import discord
from discord import app_commands
from discord.ext import commands

from typing import Optional

import asyncio
import re
import json

from credentials import DISCORD_TOKEN

extensions = [
    'ext.admin',
    'ext.card',
    'ext.misc',
    'ext.roles',
    'ext.mfw',
    'ext.banner',
    'ext.funko'
]

intents = discord.Intents.default()
intents.message_content = True

discord.utils.setup_logging()

bot = commands.Bot(command_prefix=commands.when_mentioned_or(), intents=intents)

class ButtTranslator(app_commands.Translator):
    async def translate(
        self, string: app_commands.locale_str, locale: discord.Locale,
        context: app_commands.TranslationContext) -> Optional[str]:

        trans_dict = {
            "command_name": {
                "color": {
                    "en-GB": "colour",
                    "da": "colour"
                }
            },
            "command_description": {
                "Change your role color": {
                    "en-GB": "Change your role colour",
                    "da": "Change your role colour"
                }
            },
            "parameter_description": {
                "Color hex code (e.g. #135ACF) or 'random'": {
                    "en-GB": "Colour hex code (e.g. #135ACF) or 'random'",
                    "da": "Colour hex code (e.g. #135ACF) or 'random'"
                }
            },
            "other": {
                "color": {
                    "en-GB": "colour",
                    "da": "colour"
                }
            }
        }

        try:
            return trans_dict[context.location.name][str(string)][locale.value]
        except Exception as e:
            return None


async def main():
    async with bot:
        await bot.tree.set_translator(ButtTranslator())
        for ext in extensions:
            await bot.load_extension(ext)
        await bot.start(DISCORD_TOKEN)

asyncio.run(main())
