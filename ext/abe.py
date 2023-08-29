import discord
from discord.ext import commands
from discord import app_commands

import re
from urllib.parse import urlparse
from datetime import datetime

import aiosqlite

class Abe(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command()
    async def abes(self, interaction: discord.Interaction):
        """ List the amount of abes committed in this server """
        
        async with aiosqlite.connect("ext/data/abe.db") as db:
            async with db.execute("""SELECT sum(count) FROM abe_counts
                WHERE guild_id=?""", (interaction.guild.id,)) as cursor:
                abe_count = await cursor.fetchone()

        if abe_count:
            await interaction.response.send_message(
                f"{abe_count[0]} total abes committed in this server.")
        else:
            await interaction.response.send_message(
                "No abes have been commited here.")


    @commands.Cog.listener("on_message")
    async def check_abes(self, message):

        disabled_channels = [
            230026389015756800,
            499632759040507904,
            454317864326004736,
            690007579962769479,
            926709540945293312
        ]

        # Don't check DMs, bot's posts, or disabled channels
        if not message.guild:
            return
        elif message.author == self.bot.user:
            return
        elif message.channel.id in disabled_channels:
            return

        urls = re.findall(r'(https?://\S+)', message.content)
        if not urls:
            return

        # Purge old URLs
        async with aiosqlite.connect("ext/data/abe.db") as db:
            await db.execute("""DELETE FROM url_history
                WHERE post_time <= datetime("now", "-1 day")""")
            await db.commit()

        urls = [url.lower() for url in urls]

        for url in urls:
            # regex because of people using twitter proxies 
            if re.match(r"https?://.*?twitter.*?\.com", url) or "x.com" in url:
                # Store only tweet IDs since format can change
                tw_id = re.search(r'/status/(\d+)', url)
                if tw_id:
                    url = f"tw/{tw_id[1]}"

            elif "youtu.be/" in url:
                # Expand mobile YouTube links
                yt_url = urlparse(url)
                url = (f"https://www.youtube.com/watch?v="
                    f"{yt_url.path.rsplit('/', 1)[1]}"
                    f"{f'&{yt_url.query}' if yt_url.query else ''}")

            elif "youtube.com" in url:
                # Remove cruft from pre-expanded mobile YT links
                url = url.replace("&feature=youtu.be", "")

            async with aiosqlite.connect("ext/data/abe.db") as db:
                # Check if URL has been linked before
                async with db.execute("""SELECT user_id, post_time
                    FROM url_history
                    WHERE url=? AND guild_id=? AND channel_id=?
                    ORDER BY post_time""",
                    (url, message.guild.id, message.channel.id,)) as cursor:
                    prev_posts = await cursor.fetchall()

                # If URL posted before, format and post announcement
                if prev_posts:
                    # Don't shame original posters
                    if not message.author.id == prev_posts[0][0]:
                        # Get unique users and filter out called user
                        users = list(set([message.guild.get_member(u[0]) 
                            for u in prev_posts 
                            if not u[0] == message.author.id]))
                        # Use server nickname if they have one
                        users = [u.nick if u.nick else u.name for u in users]

                        # Format the usernames prettily
                        if len(users) > 1:
                            users_format = ", ".join(users[:-1])
                            users_format += f" and {users[-1]}"
                        else:
                            users_format = users[0]

                        first = datetime.strptime(prev_posts[0][1], 
                            "%Y-%m-%d %H:%M:%S.%f%z")

                        await message.reply(
                            file=discord.File("ext/data/abe.jpg"),
                            content=(f"Already posted by "
                                f"{users_format}, first linked "
                                f"{discord.utils.format_dt(first,'R')}."))

                        await db.execute("""INSERT OR IGNORE INTO abe_counts 
                            VALUES (?, ?, ?)""",
                            (message.author.id, message.guild.id, 0))
                        await db.execute("""UPDATE abe_counts
                            SET count = count + 1
                            WHERE user_id=? AND guild_id=?""",
                            (message.author.id, message.guild.id))

                # Add URL to database
                await db.execute("""INSERT INTO url_history 
                    VALUES (?, ?, ?, ?, ?)""",
                    (url, message.author.id, message.guild.id,
                    message.channel.id, message.created_at))
                await db.commit()


async def setup(bot):
    async with aiosqlite.connect("ext/data/abe.db") as db:
        await db.execute("""CREATE TABLE IF NOT EXISTS url_history
            (url text, user_id integer, guild_id integer,
            channel_id integer, post_time integer)""")
        await db.execute("""CREATE TABLE IF NOT EXISTS abe_counts
            (user_id integer, guild_id integer, count integer, 
            UNIQUE(user_id, guild_id))""")
        await db.commit()
    await bot.add_cog(Abe(bot))
