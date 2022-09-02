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
                    "en-GB": "colour",
                    "da": "colour"
                }
            },
            "command_description": {
                "Change your role color": {
                    "en-GB": "Change your role colour",
                    "da": "Change your role colour"
                }
            },
            "parameter_description": {
                "Color hex code (e.g. #135ACF) or 'random'": {
                    "en-GB": "Colour hex code (e.g. #135ACF) or 'random'",
                    "da": "Colour hex code (e.g. #135ACF) or 'random'"
                }
            },
            "other": {
                "color": {
                    "en-GB": "colour",
                    "da": "colour"
                }
            }
        }

        try:
            return trans_dict[context.location.name][str(string)][locale.value]
        except Exception as e:
            return None