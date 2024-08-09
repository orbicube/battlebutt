import discord
from discord.ext import commands
from discord import app_commands

from howlongtobeatpy import HowLongToBeat

class HLTB(commands.Cog):

	def __init__(self, bot):
		self.bot = bot

	@app_commands.command()
	async def hltb(self, interaction: discord.Interaction, game: str):
		""" Get a game's HowLongToBeat stats """

		results = await HowLongToBeat(0.2).async_search(game, similarity_case_sensitive=False)

		if results:
			game = max(results, key=lambda element: element.similarity)

			if not game.main_story and not game.main_extra and not game.completionist:
				await interaction.response.send_message(f"{game.game_name} has no completion data available",
					ephemeral=True)
			else:
				embed = discord.Embed(
					title=game.game_name,
					url=game.game_web_link)

				if game.game_image_url:
					embed.set_image(url=game.game_image_url)

				if game.main_story:
					embed.add_field(name="Main Story", value=self.convert_hours(game.main_story))
				if game.main_extra:
					embed.add_field(name="Main + Extra", value=self.convert_hours(game.main_extra))
				if game.completionist:
					embed.add_field(name="Completionist", value=self.convert_hours(game.completionist))

			await interaction.response.send_message(embed=embed)
		else:
			await interaction.response.send_message("No game found", ephemeral=True)


	@hltb.autocomplete('game')
	async def game_autocomplete(self,
		interaction: discord.Interaction,
		current: str,) -> list[app_commands.Choice[str]]:

		results = await HowLongToBeat(0.2).async_search(current, similarity_case_sensitive=False)

		return [app_commands.Choice(name=game.game_name, value=game.game_name)
			for game in results]


	def convert_hours(self, hours):

		minutes = int((hours * 60) % 60)
		return f"{f'{int(hours)}h ' if int(hours) > 0 else ''}{f'{minutes:02d}m' if minutes > 0 else ''}"


async def setup(bot):
	await bot.add_cog(HLTB(bot))

async def teardown(bot):
	await bot.remove_cog(HLTB)