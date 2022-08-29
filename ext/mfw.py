import discord
from discord.ext import commands, tasks
from discord import app_commands

import asyncio
import aiosqlite
from glob import glob
from random import choice


class MFW(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.check_mfw.start()

    def cog_unload(self):
        self.check_mfw.cancel()

    @commands.hybrid_command()
    async def mfw(self, ctx):
        """ Posts a random reaction image """

        imgs = glob("ext/data/mfw/*.jpg") + glob("ext/data/mfw/*.png")
        await ctx.send(file=discord.File(choice(imgs)))


    @tasks.loop(seconds=60.0)
    async def check_mfw(self):
        await self.bot.wait_until_ready()

        imgs = glob("ext/data/mfw/*.jpg") + glob("ext/data/mfw/*.png")

        async with aiosqlite.connect("ext/data/mfw.db") as db:
            # Get existing image list and compare
            async with db.execute('SELECT file FROM mfw_list') as cursor:
                old_imgs = await cursor.fetchall()
            new_imgs = list(set(imgs) - set([img[0] for img in old_imgs]))

            # Put new image in db and announce
            for img in new_imgs:
                await db.execute('INSERT INTO mfw_list VALUES (?)', (img, ))
                await db.commit()

                # Get channels to post in then post them
                async with db.execute('SELECT channel_id FROM post_channels') as cursor:
                    post_channels = await cursor.fetchall()
                for c in post_channels:
                    await self.bot.get_channel(c[0]).send(
                        "New MFW added!",
                        file=discord.File(img))


    @commands.command(hidden=True)
    async def setup_mfw_db(self, ctx):

        async with aiosqlite.connect("ext/data/mfw.db") as db:
            await db.execute('CREATE TABLE IF NOT EXISTS mfw_list (file text)')
            await db.execute('CREATE TABLE IF NOT EXISTS post_channels (channel_id integer PRIMARY KEY)')
            await db.commit()


    @commands.command(hidden=True)
    @commands.is_owner()
    async def add_mfw_channel(self, ctx, channel: discord.TextChannel):
        """ Add channel for new MFW images to be announced in """

        async with aiosqlite.connect("ext/data/mfw.db") as db:
            await db.execute('INSERT INTO post_channels VALUES (?)',
                (channel.id, ))
            await db.commit()


    @commands.command(hidden=True)
    @commands.is_owner()
    async def remove_mfw_channel(self, ctx, channel: discord.TextChannel):
        """ Remove MFW announce channel """

        async with aiosqlite.connect("ext/data/mfw.db") as db:
            await db.execute('DELETE FROM post_channels WHERE channel_id=?', 
                (channel.id, ))
            await db.commit()


async def setup(bot):
    await bot.add_cog(MFW(bot))

async def teardown(bot):
    await bot.remove_cog(MFW)