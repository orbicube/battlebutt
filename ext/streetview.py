import discord
from discord.ext import commands
from discord import app_commands

from geopy.adapters import AioHTTPAdapter
from geopy.geocoders import Nominatim
import geopandas
from random import randint, choices
from PIL import Image
from io import BytesIO
import json
from typing import Optional

from credentials import GMAPS_KEY

class StreetView(commands.Cog):

	def __init__(self, bot):
		self.bot = bot

	gmaps_countries = [
		("Albania",25000),
		("Andorra",500),
		("Argentina",2000000),
		("Australia",2000000),
		("Austria",100000),
		("Bahrain",2000),
		("Bangladesh",250000),
		("Bhutan",20000),
		("Bolivia",500000),
		("Botswana",100000),
		("Brazil",4000000),
		("Bulgaria",200000),
		("Cambodia",200000),
		("Canada",2000000),
		("Chile",500000),
		("Colombia",500000),
		("Croatia",100000),
		("Curaçao",1000),
		("Czech Republic",250000),
		("Denmark",50000),
		("Dominican Republic",10000),
		("Ecuador",100000),
		("Egypt",50000),
		("El Salvador",20000),
		("Estonia",100000),
		("Eswatini",20000),
		("Falkland Islands",500),
		("Faroe Islands",2000),
		("Finland",400000),
		("France",1000000),
		("Germany",250000),
		("Ghana",150000),
		("Gibraltar",10),
		("Greece",200000),
		("Greenland",5000),
		("Guatemala",100000),
		("Hong Kong",10000),
		("Hungary",200000),
		("Iceland",100000),
		("India",3000000),
		("Indonesia",1000000),
		("Ireland",100000),
		("Isle of Man",1000),
		("Israel",25000),
		("Italy",500000),
		("Japan",1000000),
		("Jersey",500),
		("Jordan",50000),
		("Kazakhstan",200000),
		("Kenya",500000),
		("Kyrgyzstan",100000),
		("Latvia",75000),
		("Lesotho",30000),
		("Lithuania",75000),
		("Luxembourg",10000),
		("Macau",50),
		("Malaysia",300000),
		("Malta",2000),
		("Martinique",500),
		("Mexico",1500000),
		("Monaco",50),
		("Mongolia",100000),
		("Montenegro",15000),
		("Netherlands",75000),
		("New Zealand",250000),
		("Nigeria",500000),
		("North Macedonia",20000),
		("Norway",400000),
		("Palestine",7000),
		("Panama",50000),
		("Peru",1000000),
		("Philippines",300000),
		("Pitcairn Islands",100),
		("Poland",500000),
		("Portugal",100000),
		("Qatar",20000),
		("Romania",300000),
		("Russia",5000000),
		("Rwanda",50000),
		("San Marino",500),
		("São Tomé and Príncipe",1000),
		("Senegal",100000),
		("Serbia",75000),
		("Singapore",2000),
		("Slovakia",75000),
		("Slovenia",40000),
		("South Africa",1000000),
		("South Korea",200000),
		("Spain",600000),
		("Sri Lanka",100000),
		("Sweden",400000),
		("Switzerland",50000),
		("Taiwan",50000),
		("Thailand",500000),
		("Tunisia",20000),
		("Turkey",750000),
		("Uganda",10000),
		("Ukraine",300000),
		("United Arab Emirates",100000),
		("United Kingdom",250000),
		("United States",8000000),
		("Uruguay",80000),
	]
	gmaps_regions = {
		"Canada": [
			("Alberta", 10),
			("British Columbia", 8),
			("Manitoba",6),
			("New Brunswick", 2),
			("Newfoundland and Labrador",2),
			("Nova Scotia",2),
			("Ontario",10),
			("Prince Edward Island",1),
			("Quebec",10),
			("Saskatchewan",6),
			("Northwest Territories",2),
			("Yukon",2)
		],
		"Australia": [
			("New South Wales",10),
			("Queensland",10),
			("Victoria",8),
			("South Australia",6),
			("Tasmania",3),
			("Australian Capital Territory",1),
			("Western Australia",6),
			("Northern Territory",4),
			("Cocos Islands",1),
			("Christmas Island",1)
		],
		"United States": [
			("Alabama",10),
			("Alaska",4),
			("Arizona",6),
			("Arkansas",10),
			("California",30),
			("Colorado",20),
			("Connecticut",1),
			("Delaware",1),
			("Florida",10),
			("Georgia",10),
			("Hawaii",3),
			("Idaho",6),
			("Illinois",10),
			("Indiana",8),
			("Iowa",8),
			("Kansas",12),
			("Kentucky",10),
			("Louisiana",10),
			("Maine",6),
			("Maryland",3),
			("Massachusetts",3),
			("Michigan",12),
			("Minnesota",11),
			("Mississippi",10),
			("Missouri",12),
			("Montana",5),
			("Nebraska",5),
			("Nevada",6),
			("New Hampshire",3),
			("New Jersey",3),
			("New Mexico",10),
			("New York",15),
			("North Carolina",10),
			("North Dakota",5),
			("Ohio",10),
			("Oklahoma",10),
			("Oregon",10),
			("Pennsylvania",10),
			("Rhode Island",1),
			("South Carolina",8),
			("South Dakota",6),
			("Tennessee",10),
			("Texas",40),
			("Utah",12),
			("Vermont",3),
			("Virginia",10),
			("Washington",15),
			("West Virginia",4),
			("Wisconsin",10),
			("Wyoming",6),
			("District of Columbia",1),
			("American Samoa",1),
			("Guam",1),
			("Northern Mariana Islands",1),
			("Puerto Rico",2),
			("Virgin Islands",1)
		],
		"Russia": [
			("Adygea",50),
			("Altai Krai",10),
			("Altai Republic",2),
			("Amur Oblast",4),
			("Arkhangelsk Oblast",4),
			("Astrakhan Oblast",20),
			("Bashkortostan",25),
			("Belgorod Oblast",50),
			("Bryansk Oblast",30),
			("Buryatia",4),
			("Chechnya",50),
			("Chelyabinsk",40),
			("Chuvashia",10),
			("Dagestan",40),
			("Ingushetia",5),
			("Irkutsk Oblast",5),
			("Ivanovo Oblast",15),
			("Jewish Autonomous Oblast",5),
			("Kabardino-Balkaria",20),
			("Kaliningrad Oblast",20),
			("Kalmykia",7),
			("Kaluga Oblast",25),
			("Kamchatka Krai",2),
			("Karachay-Cherkessia",10),
			("Karelia",30),
			("Kemerovo Oblast",40),
			("Khabarovsk Krai",3),
			("Khakassia",10),
			("Khanty-Mansi",30),
			("Kirov Oblast",40),
			("Komi Republic",50),
			("Kostroma Oblast",10),
			("Krasnodar Krai",80),
			("Krasnoyarsk Krai",4),
			("Kurgan Oblast",20),
			("Kursk Oblast",15),
			("Leningrad Oblast",100),
			("Lipetsk Oblast",30),
			("Magadan Oblast",4),
			("Mari El",20),
			("Mordovia",25),
			("Moscow",20),
			("Moscow Oblast",100),
			("Murmansk Oblast",20),
			("Nizhny Novgorod Oblast",60),
			("North Ossetia–Alania",15),
			("Novgorod Oblast",10),
			("Novosibirsk Oblast",30),
			("Omsk Oblast",40),
			("Orenburg Oblast",20),
			("Penza Oblast",20),
			("Perm Krai",30),
			("Primorsky Krai",40),
			("Pskov Oblast",10),
			("Rostov Oblast",50),
			("Ryazan Oblast",20),
			("Saint Petersburg",20),
			("Sakha",10),
			("Sakhalin Oblast",10),
			("Samara Oblast",50),
			("Saratov Oblast",50),
			("Smolensk Oblast",40),
			("Stavropol Krai",50),
			("Tambov Oblast",30),
			("Tatarstan",60),
			("Tomsk Oblast",20),
			("Tula Oblast",30),
			("Tuva",10),
			("Tver Oblast",40),
			("Tyumen Oblast",10),
			("Udmurtia",30),
			("Ulyanovsk Oblast",20),
			("Vladimir Oblast",20),
			("Volgograd Oblast",40),
			("Vologda Oblast",5),
			("Voronezh Oblast",50),
			("Yamalo-Nenets",10),
			("Yaroslavl Oblast",30),
			("Zabaykalsky Krai",10)
		],
		"Brazil": [
			("Acre",5),
			("Alagoas",10),
			("Amapa",5),
			("Amazonas",2),
			("Bahia",10),
			("Ceara",10),
			("Distrito Federal",5),
			("Espirito Santo",10),
			("Goias", 10),
			("Maranhao",8),
			("Mato Grosso",10),
			("Mato Grosso do Sul",10),
			("Minas Gerias",10),
			("Para",5),
			("Paralba",5),
			("Parana",10),
			("Pernambuco",8),
			("Piaui",5),
			("Rio de Janeiro",8),
			("Rio Grande do Norte",6),
			("Rio Grande do Sul",10),
			("Rondonia",10),
			("Roraima",10),
			("Santa Catarina",7),
			("Sao Paulo",30),
			("Sergipe",5),
			("Tocantins",10)
		],
		"Uganda": [
			("Kampala",10),
			("Wakiso",4),
			("Nwoya",2)
		]
	}
	@app_commands.command()
	@app_commands.describe(reason="Why you're grabbing Street View imagery")
	@app_commands.describe(country="Country you want, leave empty for random")
	async def streetview(self, interaction: discord.Interaction,
		country: Optional[str], reason: Optional[str]):
		""" Get a random Google Street View image."""

		# Defer due to multiple http requests
		await interaction.response.defer()

		radius = 5000
		countries = [x[0].lower() for x in self.gmaps_countries]
		if not country or country.lower() not in countries:
			# Get random country, weighted roughly by area and coverage
			weights = [x[1] for x in self.gmaps_countries]
			country = choices(countries, weights)[0]
			radius = 499999
		query = {"country": country}

		# Filter down some larger countries to bias towards coverage
		if country in self.gmaps_regions:
			regions = [x[0] for x in self.gmaps_regions[country]]
			weights = [x[1] for x in self.gmaps_regions[country]]
			region = choices(regions, weights)[0]
			query["state"] = region

		# Get polygon of country from OSM
		async with Nominatim(
			user_agent="battlebutt",
			adapter_factory=AioHTTPAdapter,
			timeout=20
		) as geolocator:
			loc = await geolocator.geocode(
				query=query,
				language="en",
				geometry="geojson")
			poly = geopandas.read_file(json.dumps(loc.raw["geojson"]))

		# Generate random point in country, check coverage exists within 500km
		valid_point = False
		while not valid_point:
			rand_point = poly.sample_points(1)

			gmaps_url = "https://maps.googleapis.com/maps/api"
			strview_params = {
				"key": GMAPS_KEY,
				"location": f"{rand_point.y[0]},{rand_point.x[0]}",
				"size": "640x480",
				"radius": radius,
				"heading": randint(0,359),
				"pitch": randint(0,20),
				"source": "outdoor"
			}
			r = await self.bot.http_client.get(
				url=f"{gmaps_url}/streetview/metadata",
				params=strview_params)
			try:
				metadata = r.json()["location"]
				coords = f"{metadata['lat']},{metadata['lng']}"
				valid_point = True
			except:
				pass

		# Reverse geocode an address from coverage spot
		async with Nominatim(
			user_agent="battlebutt",
			adapter_factory=AioHTTPAdapter,
			timeout=20
		) as geolocator:
			loc = await geolocator.reverse(coords, language="en", zoom=17)
			address = loc.address

		# Get image, post
		r = await self.bot.http_client.get(
			url=f"{gmaps_url}/streetview",
			params=strview_params)
		strview_img = Image.open(BytesIO(r.content))

		with BytesIO() as img_binary:
			strview_img.save(img_binary, 'PNG')
			img_binary.seek(0)
			nl = "\n"
			await interaction.followup.send(
				f"{f'{reason}:{nl}' if reason else ''}[{address}](<https://google.com/maps/place/{coords}>)",
				file=discord.File(
					fp=img_binary,
					filename="streetview.png"))

	@streetview.autocomplete('country')
	async def streetview_autocomplete(self,
		interaction: discord.Interaction,
		current: str,) -> list[app_commands.Choice[str]]:

		return [app_commands.Choice(name=country[0], value=country[0])
			for country in self.gmaps_countries
			if current.lower() in country[0].lower()][:25]


async def setup(bot):
	await bot.add_cog(StreetView(bot))

async def teardown(bot):
	await bot.remove_cog(StreetView)