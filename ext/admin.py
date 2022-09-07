import discord
from discord.ext import commands
from discord import app_commands
import asyncio

from typing import Optional, Literal

class Admin(commands.Cog):
    """Administration commands"""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='reload', hidden=True)
    @commands.is_owner()
    async def _reload(self, ctx, *, ext: str):
        try:
            await self.bot.reload_extension(f"ext.{ext}")
        except Exception as e:
            await ctx.send('\N{THINKING FACE}')
            await ctx.send('{}: {}'.format(type(e).__name__, e))
        else:
            await ctx.send('\N{HEAVY LARGE CIRCLE}')

    @commands.command(name='unload', hidden=True)
    @commands.is_owner()
    async def _unload(self, ctx, *, ext: str):
        try:
            await self.bot.unload_extension(f"ext.{ext}")
        except Exception as e:
            await ctx.send('\N{THINKING FACE}')
            await ctx.send('{}: {}'.format(type(e).__name__, e))
        else:
            await ctx.send('\N{HEAVY LARGE CIRCLE}')

    @commands.command(name='load', hidden=True)
    @commands.is_owner()
    async def _load(self, ctx, *, ext: str):
        try:
            await self.bot.load_extension(f"ext.{ext}")
        except Exception as e:
            await ctx.send('\N{THINKING FACE}')
            await ctx.send('{}: {}'.format(type(e).__name__, e))
        else:
            await ctx.send('\N{HEAVY LARGE CIRCLE}')

    @commands.command(hidden=True)
    @commands.is_owner()
    async def restart(self, ctx):
        await ctx.send('Bye!')
        await self.bot.close()
        exit(1)

    @commands.command(hidden=True)
    @commands.is_owner()
    async def sync(self, ctx,
        guilds: commands.Greedy[discord.Object],
        spec: Optional[Literal["~", "*", "^", "?"]] = None) -> None:

        if not guilds:
            if spec == "~":
                synced = await ctx.bot.tree.sync(guild=ctx.guild)
            elif spec == "*":
                ctx.bot.tree.copy_global_to(guild=ctx.guild)
                synced = await ctx.bot.tree.sync(guild=ctx.guild)
            elif spec == "^":
                ctx.bot.tree.clear_commands(guild=ctx.guild)
                await ctx.bot.tree.sync(guild=ctx.guild)
                synced = []
            elif spec == "?":
                ctx.bot.tree.clear_commands(guild=None)
                await ctx.bot.tree.sync()
                synced = []
                spec = None
            else:
                synced = await ctx.bot.tree.sync()

            await ctx.send(
                f"Synced {len(synced)} commands {'globally' if spec is None else 'to the current guild.'}")
            return

        ret = 0
        for guild in guilds:
            try:
                await ctx.bot.tree.sync(guild=guild)
            except discord.HTTPException:
                pass
            else:
                ret += 1

        await ctx.send(f"Synced the tree to {ret}/{len(guilds)}.")


async def setup(bot):
    await bot.add_cog(Admin(bot))
