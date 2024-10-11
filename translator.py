import discord
from discord import app_commands

from typing import Optional

class ButtTranslator(app_commands.Translator):
    async def translate(
        self, string: app_commands.locale_str, locale: discord.Locale,
        context: app_commands.TranslationContext) -> Optional[str]:

        trans_dict = {
            "command_name": {
                "color": {
                    "en-US": "color",
                    "en-GB": "colour",
                }
            },
            "command_description": {
                "Change your role color": {
                    "en-US": "Change your role color",
                    "en-GB": "Change your role colour",
                }
            },
            "parameter_description": {
                "Color hex code (e.g. #135ACF) or 'random'": {
                    "en-US": "Color hex code (e.g. #135ACF) or 'random'",
                    "en-GB": "Colour hex code (e.g. #135ACF) or 'random'",
                }
            },
            "other": {
                "color": {
                    "en-US": "color",
                    "en-GB": "colour",
                }
            }
        }

        try:
            return trans_dict[context.location.name][str(string)][locale.value]
        except Exception as e:
            return None