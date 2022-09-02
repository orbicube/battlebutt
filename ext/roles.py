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
    @app_commands.describe(code="Color hex code (e.g. #135ACF) or 'random'")
    async def color(self, interaction: discord.Interaction, code: Optional[str]):

        # Color or colour
        c_word = await self.bot.tree.translator.translate(
            "color", interaction.locale, app_commands.TranslationContext(
            app_commands.TranslationContextLocation.other, None))
        if not c_word:
            c_word = "color"

        # Tell them their current color
        if not code:
            if interaction.user.color == discord.Color.default():
                await interaction.response.send_message(
                    f"You don't have a {c_word}.", ephemeral=True)
                return
            else:
                color = str(interaction.user.color).upper()
                await interaction.response.send_message(
                    f"Your {c_word} is {color}.", ephemeral=True)
                return

        # Grab user's unique role from DB
        async with aiosqlite.connect("ext/data/roles.db") as db:
            async with db.execute('SELECT role_id FROM role_map WHERE user_id=? AND guild_id=?',
                (interaction.user.id, interaction.guild_id)) as cursor:
                role_id = await cursor.fetchone()

            # If they don't have a 1:1 role in the DB, make one for them
            if not role_id:
                role = await interaction.guild.create_role(
                    name = interaction.user.name)
                await interaction.user.add_roles(role)
                role = await role.edit(
                    position=int(len(interaction.guild.roles)/2))

                await db.execute('INSERT INTO role_map VALUES (?, ?, ?)',
                    (interaction.user.id, interaction.guild_id, role.id))
                await db.commit()
            else:
                role = interaction.guild.get_role(role_id[0])

        old_color = str(role.color).upper()

        if code == "random":
            # discord.Color.random() gives somewhat limited results
            role = await role.edit(color=discord.Color.from_rgb(
                randint(0,255), randint(0,255), randint(0,255)))
        else:
            # Make sure they entered a viable code
            try:
                new_color = discord.Color.from_str(code)
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

            role = await role.edit(color=new_color)

        await interaction.response.send_message(
            f"Your {c_word} has been changed from {old_color} to {str(role.color).upper()}.")


    @app_commands.command()
    @app_commands.guild_only()
    async def role(self, interaction: discord.Interaction,
        action: Literal["Add", "Remove", "List"],
        role: Optional[discord.Role]):
        """ Add, remove or list publicly available roles """

        async with aiosqlite.connect("ext/data/roles.db") as db:

            if action == "List":
                # Grab all roles for given guild, list them all out
                async with db.execute('SELECT role_id FROM role_whitelist WHERE guild_id=?',
                    (interaction.guild.id,)) as cursor:
                    roles = await cursor.fetchall()

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
            async with db.execute('SELECT role_id FROM role_whitelist WHERE guild_id=? AND role_id=?',
                (interaction.guild.id, role.id)) as cursor:
                role_in_db = await cursor.fetchone()

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
    async def rolemap_json(self, ctx, guild: discord.Guild):
        # Uses a rolemap.json file keyed 'user_id': 'role_id' to map user roles 
        # for a specified guild

        with open('ext/data/rolemap.json') as f:
            data = json.load(f)

        async with aiosqlite.connect("ext/data/roles.db") as db:
            for user_id, role_id in data.items():
                await db.execute('INSERT INTO role_map VALUES (?, ?, ?)',
                    (int(user_id), guild.id, int(role_id)))
            await db.commit()


    @commands.command(hidden=True)
    @commands.is_owner()
    async def map_role(self, ctx, user: discord.User, role: discord.Role):

        async with aiosqlite.connect("ext/data/roles.db") as db:
            await db.execute('INSERT INTO role_map VALUES (?, ?, ?)',
                (user.id, ctx.guild.id, role.id))
            await db.commit()


    @commands.command(hidden=True)
    @commands.is_owner()
    async def unmap_role(self, ctx, user: discord.User, role: discord.Role):

        async with aiosqlite.connect("ext/data/roles.db") as db:
            await db.execute('DELETE FROM role_map WHERE user_id=? AND guild_id=? AND role_id=?',
                (user.id, ctx.guild.id, role.id))
            await db.commit()


    @commands.command(hidden=True)
    @commands.is_owner()
    async def list_mapped_roles(self, ctx, user: discord.User):

        async with aiosqlite.connect("ext/data/roles.db") as db:
            async with db.execute('SELECT role_id FROM role_map WHERE user_id=? and guild_id=?',
                (user.id, ctx.guild.id)) as cursor:
                roles = await cursor.fetchall()

        if not roles:
            await ctx.send("No mapped roles for {user.name}.")
        else:
            for role in roles:
                await ctx.send(f"{ctx.guild.get_role(role[0]).name} ({role[0]}")


    @commands.command(hidden=True)
    @commands.is_owner()
    async def whitelist_role(self, ctx, role: discord.Role):

        async with aiosqlite.connect("ext/data/roles.db") as db:
            await db.execute('INSERT INTO role_whitelist VALUES (?, ?)',
                (ctx.guild.id, role.id))
            await db.commit()


    @commands.command(hidden=True)
    @commands.is_owner()
    async def blacklist_role(self, ctx, role: discord.Role):

        async with aiosqlite.connect("ext/data/roles.db") as db:
            await db.execute('DELETE FROM role_whitelist WHERE guild_id=? AND role_id=?',
                (ctx.guild.id, role.id))
            await db.commit()


async def setup(bot):
    async with aiosqlite.connect("ext/data/roles.db") as db:
        await db.execute('CREATE TABLE IF NOT EXISTS role_map (user_id integer, guild_id integer, role_id integer, UNIQUE(user_id, guild_id, role_id))')
        await db.execute('CREATE TABLE IF NOT EXISTS role_whitelist (guild_id integer, role_id integer, UNIQUE(guild_id, role_id))')
        await db.commit()
    await bot.add_cog(Roles(bot))

