import discord, requests
from discord.ext import commands

class Mechanics(commands.Cog):
	def __init__(self, bot):
		self.bot = bot

	def define(self, word):
		r = requests.get(f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}")
		json = r.json()
		return (valid:=(type(json)==list), [y for x in json for y in x["meanings"]] if valid else [])

	def score(self, word):
		return len(word)

def setup(bot):
	bot.add_cog(Mechanics(bot))