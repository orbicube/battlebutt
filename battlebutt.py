import discord
from discord import app_commands
from discord.ext import commands
import asyncio

from pathlib import Path
import sys
import traceback

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
        self.tree.on_error = self.on_app_command_error

        # Load all .py files as extensions
        for file in Path("ext").glob("**/[!_]*.py"):
            if "util" not in file.parts:
                ext = ".".join(file.parts).removesuffix(".py")
                try:
                    await self.load_extension(ext)
                except Exception as e:
                    print(f"Failed to load extension {ext}: {e}")
    
    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        error = getattr(error, 'original', error)

        if isinstance(error, (commands.CommandNotFound, commands.NotOwner)):
            return

        error_msg = (f"Error in **{ctx.command}**\n\n**Type**: {type(error)}\n\n"
            f"**Error**: {error}\n\n**Traceback**:\n```")
        for t in traceback.format_tb(error.__traceback__):
            error_msg += f"{t}\n"
        error_msg += "```"

        if not isinstance(error, commands.CommandOnCooldown):
            await self.get_channel(ERROR_CHANNEL).send(error_msg[:1999])
            traceback.print_exception(
                type(error), error, error.__traceback__, file=sys.stderr)

        await ctx.reply(f"**Error**: {error}", ephemeral=True)

    async def on_app_command_error(self,
        interaction: discord.Interaction, 
        error: app_commands.AppCommandError):
        error = getattr(error, 'original', error)

        error_msg = (f"Error in **{interaction.command}**\n\n"
            f"**Type**: {type(error)}\n\n**Error**: {error}\n\n**Traceback**:\n```")
        for t in traceback.format_tb(error.__traceback__):
            error_msg += f"{t}\n"
        error_msg += "```"

        if not isinstance(error, app_commands.CommandOnCooldown):
            await self.get_channel(ERROR_CHANNEL).send(error_msg[:1999])
            traceback.print_exception(
                type(error), error, error.__traceback__, file=sys.stderr)

        await interaction.response.send_message(f"**Error**: {error}",
            ephemeral=True)



async def main():

    discord.utils.setup_logging()

    intents = discord.Intents.default()
    intents.message_content = True
    intents.members = True

    allowed_mentions = discord.AllowedMentions(
        everyone=False,
        replied_user=False)

    async with httpx.AsyncClient(http2=True) as http_client, asyncpg.create_pool(
        user=POSTGRES_USER, password=POSTGRES_PASS, database=POSTGRES_USER) as pool:

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
