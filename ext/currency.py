import discord
from discord import app_commands
from discord.ext import commands

from difflib import get_close_matches

class Currency(commands.Cog):

    currencies = ["AED", "AFN", "ALL", "AMD", "ANG", "AOA", "ARS", "AUD", 
        "AWG", "AZN", "BAM", "BBD", "BDT", "BGN", "BHD", "BIF", "BMD", "BND",
        "BOB", "BRL", "BSD", "BTC", "BTN", "BWP", "BYN", "BZD", "CAD", "CDF", 
        "CHF", "CLF", "CLP", "CNH", "CNY", "COP", "CRC", "CUC", "CUP", "CVE", 
        "CZK", "DJF", "DKK", "DOP", "DZD", "EGP", "ERN", "ETB", "EUR", "FJD", 
        "FKP", "GBP", "GEL", "GGP", "GHS", "GIP", "GMD", "GNF", "GTQ", "GYD", 
        "HKD", "HNL", "HRK", "HTG", "HUF", "IDR", "ILS", "IMP", "INR", "IQD", 
        "IRR", "ISK", "JEP", "JMD", "JOD", "JPY", "KES", "KGS", "KHR", "KMF", 
        "KPW", "KRW", "KWD", "KYD", "KZT", "LAK", "LBP", "LKR", "LRD", "LSL", 
        "LYD", "MAD", "MDL", "MGA", "MKD", "MMK", "MNT", "MOP", "MRO", "MRU", 
        "MUR", "MVR", "MWK", "MXN", "MYR", "MZN", "NAD", "NGN", "NIO", "NOK", 
        "NPR", "NZD", "OMR", "PAB", "PEN", "PGK", "PHP", "PKR", "PLN", "PYG", 
        "QAR", "RON", "RSD", "RUB", "RWF", "SAR", "SBD", "SCR", "SDG", "SEK", 
        "SGD", "SHP", "SLL", "SOS", "SRD", "SSP", "STD", "STN", "SVC", "SYP", 
        "SZL", "THB", "TJS", "TMT", "TND", "TOP", "TRY", "TTD", "TWD", "TZS", 
        "UAH", "UGX", "USD", "UYU", "UZS", "VEF", "VES", "VND", "VUV", "WST", 
        "XAF", "XAG", "XAU", "XCD", "XDR", "XOF", "XPD", "XPF", "XPT", "YER", 
        "ZAR", "ZMW", "ZWL"]

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command()
    @app_commands.describe(
        amount="Amount of money to be converted",
        from_currency="The currency to be converted from",
        to_currency="The currency to be converted into")
    async def currency(self, interaction: discord.Interaction,
        amount: float, from_currency: str, to_currency: str):
        """ Converts one currency into another """

        if from_currency.upper() not in self.currencies:
            await interaction.response.send_message(
                "`from_currency` is not a valid currency code.",
                ephemeral=True)
            return
        elif to_currency.upper() not in self.currencies:
            await interaction.response.send_message(
                "`to_currency` is not a valid currency code.",
                ephemeral=True)
            return

        params = {
            "from": from_currency,
            "to": to_currency,
            "amount": amount,
            "places": 2
        }
        r = await self.bot.http_client.get(
            "https://api.exchangerate.host/convert",
            params=params)
        result = r.json()['result']
        
        await interaction.response.send_message((
            f"{amount:.2f} {from_currency.upper()} ="
            f" **{result}** {to_currency.upper()}"))


    @currency.autocomplete("from_currency")
    @currency.autocomplete("to_currency")
    async def currency_autocomplete(self, interaction: discord.Interaction,
        current: str,) -> list[app_commands.Choice[str]]:

        return [app_commands.Choice(name=match, value=match) for match
            in get_close_matches(current.upper(), self.currencies, n=25)]


async def setup(bot):
    await bot.add_cog(Currency(bot))