import discord
from discord.ext import commands
from discord import app_commands

from typing import Optional, Literal
from random import randint
import aiosqlite

class Roles(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="color", description="Change your role color")
    @app_commands.guild_only()
    @app_commands.describe(
        code="Hex code (e.g. #123ABC), \"current\", \"random\"",
        gradient="Hex code (e.g. #123ABC), \"random\"")
    async def color(self, interaction: discord.Interaction, code: str,
        gradient: Optional[str] = None):

        # Color or colour
        c_word = await self.bot.tree.translator.translate(
            "color", interaction.locale, app_commands.TranslationContext(
            app_commands.TranslationContextLocation.other, None))
        if not c_word:
            c_word = "color"

        # Tell them their current color
        if code.lower() == "current":
            if interaction.user.color == discord.Color.default():
                await interaction.response.send_message(
                    f"You don't have a {c_word}.", ephemeral=True)
                return
            else:
                color = str(interaction.user.color).upper()
                if old_gradient := interaction.user.secondary_color:
                    color = f"{color}→{str(old_gradient).upper()}"
                await interaction.response.send_message(
                    f"Your {c_word} is {color}.", ephemeral=True)
                return

        # Grab user's unique role from DB
        role_id = await self.bot.db.fetchrow("""SELECT role_id FROM role_map
            WHERE user_id=$1 AND guild_id=$2""",
            interaction.user.id, interaction.guild_id)

        # If they don't have a 1:1 role in the DB, make one for them
        if not role_id:
            role = await interaction.guild.create_role(
                name = interaction.user.name)
            await interaction.user.add_roles(role)
            role = await role.edit(
                position=int(len(interaction.guild.roles)/2))

            await self.bot.db.execute(
                "INSERT INTO role_map VALUES ($1, $2, $3)",
                interaction.user.id, interaction.guild_id, role.id)
        else:
            role = interaction.guild.get_role(role_id[0])

        old_color = str(role.color).upper()
        if old_gradient := role.secondary_color:
            old_color = f"{old_color}→{str(old_gradient).upper()}"

        new_codes = [code.lower()]
        if gradient:
            new_codes.append(gradient.lower())
        
        new_colors = []
        for c in new_codes:
            if c.lower() == "random":
                new_color = discord.Color.from_rgb(
                    randint(0,255), randint(0,255), randint(0,255))
            else:
                # Make sure they entered a viable code
                if not c.startswith("#"):
                    c = f"#{c}"

                try:
                    new_color = discord.Color.from_str(c)
                except ValueError:
                    await interaction.response.send_message(
                        "That wasn't a valid hex code.", ephemeral=True)
                    return

                # Checking against invisible name combos (plus or minus 5)
                if 49 <= new_color.r <= 49:
                    if 52 <= new_color.g <= 62:
                        if 58 <= new_color.b <= 68:
                            await interaction.response.send_message(
                                "I'm not letting you turn invisible.",
                                ephemeral=True)
                            return

            new_colors.append(new_color)

        if len(new_colors) == 2:
            role = await role.edit(color=new_colors[0],
                secondary_color=new_colors[1])
            new_str = (f"{str(new_colors[0]).upper()}→"
                f" {str(new_colors[1]).upper()}")
        else:
            role = await role.edit(color=new_colors[0])
            new_str = str(new_colors[0]).upper()

        await interaction.response.send_message(
            f"Your {c_word} has been changed from {old_color} to {new_str}.")

    @app_commands.command()
    @app_commands.guild_only()
    async def role(self, interaction: discord.Interaction,
        action: Literal["Add", "Remove", "List"],
        role: Optional[discord.Role]):
        """ Add, remove or list publicly available roles """

        if action == "List":
            # Grab all roles for given guild, list them all out
            roles = await self.bot.db.fetch("""SELECT role_id FROM role_whitelist
                WHERE guild_id=$1""", interaction.guild.id)

            if roles:
                roles = [interaction.guild.get_role(role[0]).mention for role in roles]
                await interaction.response.send_message(
                    f"**Available roles**:\n\n{', '.join(roles)}",
                    ephemeral=True)
                return
            else:
                await interaction.response.send_message(
                    "This server doesn't have any available roles.",
                    ephemeral=True)
                return
        else:
            # If Add/Remove, need to specify role argument
            if not role:
                await interaction.response.send_message(
                    "You need to specify a role.", ephemeral=True)
                return

        # Check if role is whitelisted to be freely added
        role_in_db = await self.bot.db.fetchrow(
            """SELECT role_id FROM role_whitelist
            WHERE guild_id=$1 AND role_id=$2""",
            interaction.guild.id, role.id)

        if not role_in_db:
            await interaction.response.send_message(
                "That role isn't whitelisted.", ephemeral=True)
            return

        if action == "Add":
            if role in interaction.user.roles:
                await interaction.response.send_message(
                    "You already have that role.", ephemeral=True)
            else:
                await interaction.user.add_roles(role)
                await interaction.response.send_message(
                    f"{role.mention} role granted.", ephemeral=True)
        else:
            if role not in interaction.user.roles:
                await interaction.response.send_message(
                    "You don't have that role.", ephemeral=True)
            else:
                await interaction.user.remove_roles(role)
                await interaction.response.send_message(
                    f"{role.mention} role removed.", ephemeral=True)


    @commands.command(hidden=True)
    @commands.is_owner()
    async def rolemap_json(self, ctx):
        # Uses a rolemap.json file keyed 'user_id': 'role_id' to map user roles 

        with open('ext/data/rolemap.json') as f:
            data = json.load(f)

        for user_id, role_id in data.items():
            await self.bot.db.execute(
                "INSERT INTO role_map VALUES ($1, $2, $3)",
                int(user_id), ctx.guild.id, int(role_id))


    @commands.command(hidden=True)
    @commands.is_owner()
    async def map_role(self, ctx, user: discord.User, role: discord.Role):

        await db.execute("INSERT INTO role_map VALUES ($1, $2, $3)",
            user.id, ctx.guild.id, role.id)


    @commands.command(hidden=True)
    @commands.is_owner()
    async def unmap_role(self, ctx, user: discord.User, role: discord.Role):

        await self.bot.db.execute("""DELETE FROM role_map
            WHERE user_id=$1 AND guild_id=$2 AND role_id=$3""",
            user.id, ctx.guild.id, role.id)


    @commands.command(hidden=True)
    @commands.is_owner()
    async def list_mapped_roles(self, ctx, user: discord.User):

        roles = await self.bot.db.execute("""SELECT role_id FROM role_map
            WHERE user_id=$1 AND guild_id=$2""",
            user.id, ctx.guild.id)

        if not roles:
            await ctx.send("No mapped roles for {user.name}.")
        else:
            for role in roles:
                await ctx.send(
                    f"{ctx.guild.get_role(role[0]).name} ({role[0]}")


    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.command()
    async def whitelist(self, interaction: discord.Interaction,
        action: Literal["Add", "Remove"], role: discord.Role):
        """ Add or remove a role to the whitelist. """

        if action == "Add":
            if role.permissions.administrator:
                await interaction.response.send_message(
                    f"Can't whitelist a role that has admin priviliges.",
                    ephemeral=True)
                return
            elif role.id == interaction.guild.id:
                await interaction.response.send_message(
                    f"Can't whitelist @everyone. It doesn't even do anything.",
                    ephemeral=True)

            try:
                await self.bot.db.execute(
                    "INSERT INTO role_whitelist VALUES ($1, $2)",
                    interaction.guild.id, role.id)
            except:
                await interaction.response.send_message(
                    f"That role has already been added.",
                    ephemeral=True)

            await interaction.response.send_message(
                f"Added {role.name} to the role whitelist.")
            
        else:
            await self.bot.db.execute("""DELETE FROM role_whitelist
                WHERE guild_id=$1 AND role_id=$2""",
                interaction.guild.id, role.id)

            await interaction.response.send_message(
                f"Removed {role.name} from the whitelist.")


    @commands.Cog.listener("on_guild_role_update")
    async def check_mentionable(self, before, after):
        """ Change whitelist if mentionable status has changed """
        if before.mentionable != after.mentionable:
            if after.mentionable:                
                # Don't let people add admin roles to list
                if after.permissions.administrator:
                    return

                await self.bot.db.execute(
                    "INSERT INTO role_whitelist VALUES ($1, $2)",
                    after.guild.id, after.id)
            else:
                await self.bot.db.execute("""DELETE FROM role_whitelist
                    WHERE guild_id=$1 AND role_id=$2""",
                    after.guild.id, after.id)


    @commands.Cog.listener("on_guild_role_delete")
    async def clean_list(self, deleted_role):
        """ If deleted role was mentionable, remove it from the list """
        if deleted_role.mentionable:
            await self.bot.db.execute("""DELETE FROM role_whitelist
                WHERE guild_id=$1 AND role_id=$2""",
                deleted_role.guild.id, deleted_role.id)


    @commands.command(hidden=True)
    @commands.is_owner()
    async def role_cleanup(self, ctx):
        roles = await self.bot.db.fetch("""SELECT role_id FROM role_whitelist
            WHERE guild_id=$1""", ctx.guild.id)

        for role in roles:
            if not ctx.guild.get_role(role[0]):
                await self.bot.db.execute("""DELETE FROM role_whitelist
                    WHERE guild_id=$1 AND role_id=$2""", ctx.guild.id, role[0])
                await ctx.send(f"Deleted {role[0]}")


async def setup(bot):
    async with aiosqlite.connect("ext/data/roles.db") as db:
        await bot.db.execute("""CREATE TABLE IF NOT EXISTS role_map
            (user_id bigint, guild_id bigint, role_id bigint, 
            UNIQUE(user_id, guild_id))""")
        await bot.db.execute("""CREATE TABLE IF NOT EXISTS role_whitelist
            (guild_id bigint, role_id bigint, UNIQUE(guild_id, role_id))""")
    await bot.add_cog(Roles(bot))

