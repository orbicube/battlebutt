import discord
from discord.ext import commands
from discord import app_commands
import asyncio

import traceback
from credentials import ERROR_CHANNEL

class ErrorHandler(commands.Cog):

	def __init__(self, bot):
		self.bot = bot
		bot.tree.error = self.on_app_command_error


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
	        await self.bot.get_channel(ERROR_CHANNEL).send(error_msg[:1999])
	        traceback.print_exception(
	            type(error), error, error.__traceback__, file=sys.stderr)

	    await interaction.response.send_message(f"**Error**: {error}",
	        ephemeral=True)


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
	        await self.bot.get_channel(ERROR_CHANNEL).send(error_msg[:1999])
	        traceback.print_exception(
	            type(error), error, error.__traceback__, file=sys.stderr)

	    await ctx.reply(f"**Error**: {error}", ephemeral=True)


async def setup(bot):
	await bot.add_cog(ErrorHandler(bot))