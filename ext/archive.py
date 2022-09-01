import discord
from discord.ext import commands
from discord import app_commands

from typing import Optional

class Archive(commands.Cog):

    # guild.id: channel.id
    archive_channels = {
        122087203760242692: 851585447918174248,
        143562235740946432: 402750968099373057
    }
    # channel.id: "desired_name"
    channel_aliases = {
        122087203760242692: "general",
        291972702514708500: "gamepol",
        230026389015756800: "uspol",
        454317864326004736: "worldpol",
        521408449507229701: "algorithm-curses",
        122197647464464387: "anime",
        122197670524747777: "wrestling",
        690007579962769479: "vtubers"
    }

    def __init__(self, bot):
        self.bot = bot
        self.archive_ctx = app_commands.ContextMenu(
            name='Archive Post',
            callback=self.archive)
        self.bot.tree.add_command(self.archive_ctx)

    async def cog_unload(self):
        self.bot.tree.remove_command(
            self.archive_ctx.name,
            type=self.archive_ctx.type)

    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def archive(self, interaction: discord.Interaction, msg: discord.Message):
        """ Archive a message in the archival channel. """

        # Check for channel use for archival
        try:
            post_channel = self.bot.get_channel(
                self.archive_channels[interaction.guild.id])
        except:
            await interaction.response.send_message(
                "This server doesn't have an archive channel.",
                ephemeral=True)
            return

        archival = discord.Embed(
            description = msg.clean_content,
            timestamp = msg.created_at,
            colour = msg.author.colour
        )

        archival.set_author(
            name = msg.author.name,
            icon_url = msg.author.display_avatar.url,
            url = msg.jump_url
        )

        # If a channel's name changes often for jokes, use a generic name
        try:
            chan_name = self.channel_aliases[msg.channel.id]
        except:
            chan_name = msg.channel.name
        archival.set_footer(text=f"#{chan_name}")

        if msg.attachments:
            archival.set_image(url=msg.attachments[0].url)

        await post_channel.send(embed=archival)
        await interaction.response.send_message(
            f"Archived this post: {msg.jump_url}")


async def setup(bot):
    await bot.add_cog(Archive(bot))

async def teardown(bot):
    await bot.remove_cog(Archive)