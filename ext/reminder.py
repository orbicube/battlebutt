import discord
from discord.ext import commands, tasks
from discord import app_commands

from dateparser import parse
from datetime import datetime
import re
import aiosqlite

import sys
import traceback

from credentials import DEBUG_CHANNEL

class Reminder(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.reminder_task.start()

    def cog_unload(self):
        self.reminder_task.cancel()

    @app_commands.command()
    @app_commands.describe(
        time=("Natural language or Discord timestamp e.g. \"1 week\", "
        "\"4 days 3 hours\", <t:1234567890:R>"),
        memo="What you want the bot to remind you about")
    async def remind(self, interaction: discord.Interaction,
        time: str, memo: str):
        """ Set a reminder in the future """

        # If bot can @everyone then this is a vector
        if "@everyone" in memo or "@here" in memo:
            await interaction.response.send_message(
                "I'm not letting you @everyone.", ephemeral=True)
            return

        # Check for Discord timestamp
        timestamp = re.match(r"<t:(\d+):.>", time)
        if timestamp:
            time = timestamp[1]

        time = parse(time, settings={
            "PREFER_DATES_FROM": "future",
            "RETURN_AS_TIMEZONE_AWARE": True})
        if not time:
            await interaction.response.send_message(
                "I couldn't parse that time.", ephemeral=True)
            return
        time = time.replace(microsecond=0)

        await self.bot.db.execute(
            "INSERT INTO reminder VALUES ($1, $2, $3, $4)",
            interaction.user.id, interaction.channel_id, time, memo)

        if self.reminder_task.is_running():
            self.reminder_task.restart()
        else:
            self.reminder_task.start()        

        await interaction.response.send_message(
            f"I'll remind you {discord.utils.format_dt(time, 'R')}.")
        

    @tasks.loop()
    async def reminder_task(self):
        await self.bot.wait_until_ready()

        reminder = await self.bot.db.fetchrow(
            """SELECT * FROM reminder ORDER BY remind_time ASC""")

        await self.bot.get_channel(DEBUG_CHANNEL).send(str(reminder))

        if not reminder:
            self.reminder_task.stop()
            return

        await discord.utils.sleep_until(reminder[2])

        try:
            await self.bot.get_channel(reminder[1]).send(
                f"**Reminder** for <@{reminder[0]}>: {reminder[3]}")
        except:
            pass

        await self.bot.db.execute("""DELETE FROM reminder WHERE
                user_id=$1 and channel_id=$2 and
                remind_time=$3 and remind_memo=$4""",
                reminder[0], reminder[1], reminder[2], reminder[3])


    @reminder_task.error
    async def reminder_task_error(self, error):
        error = getattr(error, 'original', error)

        error_msg = (f"Error in **reminder.reminder_task()**:"
            f"**Type**: {type(error)}\n\n**Error**: {error}\n\n"
            "**Traceback**:\n```")
        for t in traceback.format_tb(error.__traceback__):
            error_msg += f"{t}\n"
        error_msg += "```"

        await self.bot.get_channel(DEBUG_CHANNEL).send(error_msg)
        traceback.print_exception(
            type(error), error, error.__traceback__, file=sys.stderr)


async def setup(bot):
    await bot.db.execute("""CREATE TABLE IF NOT EXISTS reminder
            (user_id bigint, channel_id bigint,
            remind_time timestamp with time zone, remind_memo text)""")

    await bot.add_cog(Reminder(bot))

async def teardown(bot):
    await bot.remove_cog(Reminder)