import discord
from discord.ext import commands, tasks
from discord import app_commands

import aiosqlite
from datetime import datetime
import time
import re
from typing import Optional

import traceback
import sys

from credentials import TWITCH_ID, TWITCH_SECRET, ERROR_CHANNEL

class Twitch(commands.Cog):

    post_channels = [
        143562235740946432
    ]

    def __init__(self, bot):
        self.bot = bot
        self.check_twitch.start()

    def cog_unload(self):
        self.check_twitch.cancel()


    @tasks.loop(minutes=2.0)
    async def check_twitch(self):
        await self.bot.wait_until_ready()

        # Setup Twitch API auth
        headers = await self.twitch_auth()

        # Put all channels and their stored live status in a dict
        channels = {}
        async with aiosqlite.connect("ext/data/twitch.db") as db:
            async with db.execute("""SELECT channel, live 
                FROM twitch_live""") as cursor:
                async for row in cursor:
                    channels[row[0]] = row[1]
        if not channels:
            return

        params = {
            "user_login": list(channels.keys()) 
        }
        try:
            r = await self.bot.http_client.get(
                "https://api.twitch.tv/helix/streams",
                headers=headers, params=params)
            streams = r.json()["data"]
        except Exception as e:
            await self.bot.get_channel(ERROR_CHANNEL).send(
                f"Error in twitch.check_twitch(): {type(e)} {e}")
            return

        for stream in streams:
            # If we haven't stored it being live, time to post
            if not channels[stream["user_login"]]:

                embed = await self.compose_embed(stream, headers)

                for c in self.post_channels:
                    chan = self.bot.get_channel(c)

                    role = discord.utils.find(
                        lambda r: r.name.lower() == stream["user_login"],
                        chan.guild.roles)
                    if role:
                        msg = f"{role.mention} is live:"
                    else:
                        msg = f"{stream['user_name']} is live:"

                    await chan.send(msg, embed=embed)

                async with aiosqlite.connect("ext/data/twitch.db") as db:
                    await db.execute("""UPDATE twitch_live SET live = 1
                        WHERE channel=?""", (stream["user_login"],))
                    await db.commit()

        # Get list of newly offline channels and set offline
        offline = [item for item in 
            [chan for (chan, live) in channels.items() if live]
            if item not in [stream["user_login"] for stream in streams]]
        for chan in offline:
            async with aiosqlite.connect("ext/data/twitch.db") as db:
                await db.execute("""UPDATE twitch_live SET live = 0
                    WHERE channel=?""", (chan,))
                await db.commit()

    @check_twitch.error
    async def check_twitch_error(self, error):
        error = getattr(error, 'original', error)

        error_msg = (f"Error in **twitch.check_twitch()**\n\n"
            f"**Type**: {type(error)}\n\n**Error**: {error}\n\n"
            "**Traceback**:\n```")
        for t in traceback.format_tb(error.__traceback__):
            error_msg += f"{t}\n"
        error_msg += "```"

        await self.bot.get_channel(ERROR_CHANNEL).send(error_msg)
        traceback.print_exception(
            type(error), error, error.__traceback__, file=sys.stderr)



    @app_commands.describe(channel="Twitch channel name or URL")
    @commands.hybrid_command(name="twitch", hidden=True)
    async def get_twitch(self, ctx, channel: str):
        """ Post a nicer Discord embed of the given Twitch channel """

        url_match = re.search(r"(?:twitch.tv/)(\w+)/?", channel)
        if url_match:
            channel = url_match[1]

        # Setup Twitch API auth
        headers = await self.twitch_auth()
        params = {
            "user_login": channel
        }
        r = await self.bot.http_client.get(
            "https://api.twitch.tv/helix/streams",
            headers=headers, params=params)
        stream = r.json()["data"]

        if not stream:
            try:
                error_test = await self.compose_embed(
                    {"user_login": channel}, headers)
            except KeyError:
                # Channel exists
                await ctx.reply(
                    "That channel isn't currently streaming.", ephemeral=True)
            except IndexError:
                # Channel does not exist
                await ctx.reply(
                    "That isn't a valid Twitch channel.", ephemeral=True)
            return


        embed = await self.compose_embed(stream[0], headers)

        #embed.description = f"{stream[0]['viewer_count']} viewers"
        embed.add_field(name="Viewers", value=stream[0]["viewer_count"])
        embed.timestamp = datetime.strptime(
            stream[0]['started_at'], "%Y-%m-%dT%H:%M:%S%z")

        await ctx.reply(embed=embed)


    @commands.Cog.listener("on_message")
    async def detect_twitch_links(self, message):
        """ If a Twitch link is a currently live streamer, replace embed """
        if message.author == self.bot.user:
            return

        twitch_urls = re.findall(
            r"https?://(?:www\.)?twitch\.tv/(\w+)/?(?!\S)",
            message.content)
        if not twitch_urls:
            return

        await message.edit(suppress=True)

        headers = await self.twitch_auth()
        params = {
            "user_login": twitch_urls
        }
        r = await self.bot.http_client.get(
            "https://api.twitch.tv/helix/streams",
            headers=headers, params=params)
        streams = r.json()["data"]

        embeds = []
        for stream in streams:
            embed = await self.compose_embed(stream, headers)
            embed.add_field(name="Viewers", value=stream["viewer_count"])
            embed.timestamp = datetime.strptime(
                stream['started_at'], "%Y-%m-%dT%H:%M:%S%z")
            embeds.append(embed)

        if embeds:
            await message.reply(embeds=embeds)


    async def compose_embed(self, stream, headers):

        params = {"login": stream["user_login"]}
        r = await self.bot.http_client.get(
            "https://api.twitch.tv/helix/users",
            headers=headers, params=params)
        icon_url = r.json()["data"][0]["profile_image_url"]

        embed = discord.Embed(
            title=stream["title"],
            url=f"https://www.twitch.tv/{stream['user_login']}",
            colour=0x6441a4)
        embed.set_author(
            name=stream["user_name"],
            icon_url=icon_url)
        embed.set_footer(
            text=stream["game_name"],
            icon_url="https://i.imgur.com/nhlnbjR.png"
        )

        thumb_img = stream["thumbnail_url"] + f"?t={int(time.time())}"
        thumb_img = thumb_img.replace("{width}", "1920")
        thumb_img = thumb_img.replace("{height}", "1080")
        embed.set_image(url=thumb_img)

        return embed


    async def twitch_auth(self):

        async with aiosqlite.connect("ext/data/twitch.db") as db:
            async with db.execute("""SELECT token, expiry FROM twitch_auth 
                ORDER BY expiry DESC""") as cursor:
                try:
                    token, expiry = await cursor.fetchone()
                except:
                    token, expiry = 0, 0

        if not token or (int(time.time()) + 120) > expiry:
            params = {
                "client_id": TWITCH_ID,
                "client_secret": TWITCH_SECRET,
                "grant_type": "client_credentials"
            }
            r = await self.bot.http_client.post(
                "https://id.twitch.tv/oauth2/token", params=params)
            js = r.json()

            async with aiosqlite.connect("ext/data/twitch.db") as db:
                await db.execute("INSERT INTO twitch_auth VALUES (?, ?)",
                    (js["access_token"], (int(time.time())+js["expires_in"])))
                await db.commit()

        headers = {
            "client-id": TWITCH_ID,
            "Authorization": f"Bearer {token}"
        }

        return headers


    @commands.command(hidden=True)
    async def add_twitch(self, ctx, channel):

        async with aiosqlite.connect("ext/data/twitch.db") as db:
            await db.execute("""INSERT INTO twitch_live
                VALUES (?, ?)""", (channel, 0))
            await db.commit()


    @commands.command(hidden=True)
    async def remove_twitch(self, ctx, channel):

        async with aiosqlite.connect("ext/data/twitch.db") as db:
            await db.execute("""DELETE FROM twitch_live
                WHERE channel=?""", (channel,))
            await db.commit()


async def setup(bot):
    async with aiosqlite.connect("ext/data/twitch.db") as db:
        await db.execute("""CREATE TABLE IF NOT EXISTS twitch_live
            (channel text, live integer, UNIQUE(channel))""")
        await db.execute("""CREATE TABLE IF NOT EXISTS twitch_auth
            (token text, expiry integer)""")
        await db.commit()

    await bot.add_cog(Twitch(bot))

async def teardown(bot):
    await bot.remove_cog(Twitch)






                
