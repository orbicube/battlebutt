import discord
from discord.ext import commands
import asyncio

import checks

class Admin:
    """Administration commands"""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='reload', hidden=True)
    @checks.is_owner()
    async def _reload(self, ctx, *, module : str):
        """Reloads a module."""
        try:
            self.bot.unload_extension(module)
            self.bot.load_extension(module)
        except Exception as e:
            await ctx.send('\N{THINKING FACE}')
            await ctx.send('{}: {}'.format(type(e).__name__, e))
        else:
            await ctx.send('\N{HEAVY LARGE CIRCLE}')

    @commands.command(hidden=True)
    @checks.is_owner()
    async def restart(self, ctx):
        await ctx.send('Bye!')
        await self.bot.logout()
        exit(1)


def setup(bot):
    bot.add_cog(Admin(bot))
