import discord
from discord.ext import commands
import asyncio

import glob
import random


class mfw:

    def __init__(self, bot):
        self.bot = bot


    @commands.command(aliases=['tfw'], pass_context=True)
    @commands.cooldown(rate=3, per=30)
    async def mfw(self, ctx):
        jpgs = glob.glob("mfw/*.jpg")
        pngs = glob.glob("mfw/*.png")
        all_imgs = jpgs + pngs

        selected_img = random.choice(all_imgs)

        await ctx.send(file=discord.File(selected_img))


def setup(bot):
    bot.add_cog(mfw(bot))
