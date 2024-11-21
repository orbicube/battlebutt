import discord
from discord import app_commands
from discord.ext import commands
import asyncio

from pathlib import Path
import sys

import httpx
import asyncpg

from credentials import DISCORD_TOKEN, ERROR_CHANNEL, DEBUG_CHANNEL, POSTGRES_USER, POSTGRES_PASS
from translator import ButtTranslator
from typing import Optional


class Battlebutt(commands.Bot):
    def __init__(
        self,
        *args,
        db: asyncpg.Pool,
        http_client: httpx.AsyncClient,
        error_channel: Optional[int] = None,
        debug_channel: Optional[int] = None,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.db = db
        self.http_client = http_client


    async def setup_hook(self) -> None:

        for file in Path("ext").glob("**/[!_]*.py"):
            ext = ".".join(file.parts).removesuffix(".py")
            try:
                await self.load_extension(ext)
            except Exception as e:
                print(f"Failed to load extension {ext}: {e}")


async def main():

    discord.utils.setup_logging()

    intents = discord.Intents.default()
    intents.message_content = True
    intents.members = True

    allowed_mentions = discord.AllowedMentions(
        everyone=False,
        replied_user=False)

    async with httpx.AsyncClient(http2=True) as http_client, asyncpg.create_pool(
        user=POSTGRES_USER, password=POSTGRES_PASS, database="battlebutt") as pool:

        async with Battlebutt(
            command_prefix=commands.when_mentioned_or('/'),
            case_insensitive=True,  
            intents=intents,
            allowed_mentions=allowed_mentions,
            db=pool,
            http_client=http_client,
        ) as bot:
            await bot.tree.set_translator(ButtTranslator())
            await bot.start(DISCORD_TOKEN)


asyncio.run(main())
