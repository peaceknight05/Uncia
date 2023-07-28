import discord, os
from discord.ext import commands

class Utils(commands.Cog):
	def __init__(self, bot):
		self.bot = bot

	@commands.slash_command(description="Reloads all cogs.")
	@commands.is_owner()
	async def reload(self, ctx):
		for filename in os.listdir("./cogs"):
			if filename.endswith(".py"):
				self.bot.reload_extension(f"cogs.{filename[:-3]}")
		await ctx.respond("Cogs reloaded!")

def setup(bot):
	bot.add_cog(Utils(bot))