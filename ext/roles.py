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
        code="Hex code (e.g. #123ABC), \"current\", \"random\"")
    async def color(self, interaction: discord.Interaction, code: str):

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
                await interaction.response.send_message(
                    f"Your {c_word} is {color}.", ephemeral=True)
                return

        # Grab user's unique role from DB
        async with aiosqlite.connect("ext/data/roles.db") as db:
            async with db.execute("""SELECT role_id FROM role_map
                WHERE user_id=? AND guild_id=?""",
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

        if code.lower() == "random":
            # discord.Color.random() gives somewhat limited results
            role = await role.edit(color=discord.Color.from_rgb(
                randint(0,255), randint(0,255), randint(0,255)))
        else:
            # Make sure they entered a viable code
            if not code.startswith("#"):
                code = f"#{code}"
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

        await interaction.response.send_message((
            f"Your {c_word} has been changed from {old_color}"
            f" to {str(role.color).upper()}."))


    @app_commands.command()
    @app_commands.guild_only()
    async def role(self, interaction: discord.Interaction,
        action: Literal["Add", "Remove", "List"],
        role: Optional[discord.Role]):
        """ Add, remove or list publicly available roles """

        async with aiosqlite.connect("ext/data/roles.db") as db:
            if action == "List":
                # Grab all roles for given guild, list them all out
                async with db.execute("""SELECT role_id FROM role_whitelist
                    WHERE guild_id=?""",
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
            async with db.execute("""SELECT role_id FROM role_whitelist
                WHERE guild_id=? AND role_id=?""",
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
    async def rolemap_json(self, ctx):
        # Uses a rolemap.json file keyed 'user_id': 'role_id' to map user roles 

        with open('ext/data/rolemap.json') as f:
            data = json.load(f)

        async with aiosqlite.connect("ext/data/roles.db") as db:
            for user_id, role_id in data.items():
                await db.execute('INSERT INTO role_map VALUES (?, ?, ?)',
                    (int(user_id), ctx.guild.id, int(role_id)))
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
            await db.execute("""DELETE FROM role_map
                WHERE user_id=? AND guild_id=? AND role_id=?""",
                (user.id, ctx.guild.id, role.id))
            await db.commit()


    @commands.command(hidden=True)
    @commands.is_owner()
    async def list_mapped_roles(self, ctx, user: discord.User):

        async with aiosqlite.connect("ext/data/roles.db") as db:
            async with db.execute("""SELECT role_id FROM role_map
                WHERE user_id=? AND guild_id=?""",
                (user.id, ctx.guild.id)) as cursor:
                roles = await cursor.fetchall()

        if not roles:
            await ctx.send("No mapped roles for {user.name}.")
        else:
            for role in roles:
                await ctx.send(f"{ctx.guild.get_role(role[0]).name} ({role[0]}")


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
                async with aiosqlite.connect("ext/data/roles.db") as db:
                    await db.execute('INSERT INTO role_whitelist VALUES (?, ?)',
                        (interaction.guild.id, role.id))
                    await db.commit()
            except:
                await interaction.response.send_message(
                    f"That role has already been added.",
                    ephemeral=True)

            await interaction.response.send_message(
                f"Added {role.name} to the role whitelist.")
            
        else:
            async with aiosqlite.connect("ext/data/roles.db") as db:
                await db.execute("""DELETE FROM role_whitelist
                    WHERE guild_id=? AND role_id=?""",
                    (interaction.guild.id, role.id))
                await db.commit()

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

                async with aiosqlite.connect("ext/data/roles.db") as db:
                    await db.execute('INSERT INTO role_whitelist VALUES (?, ?)',
                        (after.guild.id, after.id))
                    await db.commit()
            else:
                async with aiosqlite.connect("ext/data/roles.db") as db:
                    await db.execute("""DELETE FROM role_whitelist
                        WHERE guild_id=? AND role_id=?""",
                        (after.guild.id, after.id))
                    await db.commit()


    @commands.Cog.listener("on_guild_role_delete")
    async def clean_list(self, deleted_role):
        """ If deleted role was mentionable, remove it from the list """
        if deleted_role.mentionable:
            async with aiosqlite.connect("ext/data/roles.db") as db:
                await db.execute("""DELETE FROM role_whitelist
                    WHERE guild_id=? AND role_id=?""",
                    (deleted_role.guild.id, deleted_role.id))
                await db.commit()


    @commands.command(hidden=True)
    @commands.is_owner()
    async def role_cleanup(self, ctx):
        async with aiosqlite.connect("ext/data/roles.db") as db:
            async with db.execute("""SELECT role_id FROM role_whitelist
                WHERE guild_id=?""", (ctx.guild.id,)) as cursor:
                roles = await cursor.fetchall()

            for role in roles:
                if not ctx.guild.get_role(role[0]):
                    await db.execute("""DELETE FROM role_whitelist
                        WHERE guild_id=? AND role_id=?""",
                        (ctx.guild.id, role[0]))
                    await db.commit()
                    await ctx.send(f"Deleted {role[0]}")


async def setup(bot):
    async with aiosqlite.connect("ext/data/roles.db") as db:
        await db.execute('CREATE TABLE IF NOT EXISTS role_map (user_id integer, guild_id integer, role_id integer, UNIQUE(user_id, guild_id))')
        await db.execute('CREATE TABLE IF NOT EXISTS role_whitelist (guild_id integer, role_id integer, UNIQUE(guild_id, role_id))')
        await db.commit()
    await bot.add_cog(Roles(bot))

