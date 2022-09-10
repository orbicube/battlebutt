import discord
from discord.ext import commands, tasks
from discord import app_commands

import aiosqlite
from glob import glob
from random import choice
from typing import Optional

class MFW(commands.Cog):

    post_channels = [
        143562235740946432
    ]

    def __init__(self, bot):
        self.bot = bot
        self.check_mfw.start()

    async def cog_unload(self):
        self.check_mfw.cancel()

    @commands.hybrid_command()
    @app_commands.describe(reason="What you're reacting to")
    async def mfw(self, ctx, reason: str):
        """ Posts a random reaction image """

        imgs = glob("ext/data/mfw/*.jpg") + glob("ext/data/mfw/*.png")
        if reason and ctx.interaction:
            await ctx.send(f"mfw {reason}:",
                file=discord.File(choice(imgs)))
        else:
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

                for c in self.post_channels:
                    await self.bot.get_channel(c).send(
                        "New MFW added!",
                        file=discord.File(img))

            await db.commit()


async def setup(bot):
    async with aiosqlite.connect("ext/data/mfw.db") as db:
        await db.execute('CREATE TABLE IF NOT EXISTS mfw_list (file text)')
        await db.commit()
    await bot.add_cog(MFW(bot))

async def teardown(bot):
    await bot.remove_cog(MFW)