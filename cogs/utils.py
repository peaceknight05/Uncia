import os
import discord
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

	@commands.slash_command(description="Define a word.")
	async def define(
		self,
		ctx,
		word: discord.Option(discord.SlashCommandOptionType.string),
		hidden: discord.Option(discord.SlashCommandOptionType.boolean, default=False)
	):
		w = word.lower()
		meanings = self.bot.get_cog('Mechanics').define(w)[1]
		if not len(meanings):
			embed = discord.Embed(
				title=w.capitalize(),
				description=f"\"{w}\" is not a valid word!",
				color=0xFF8888
			)
			embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
		else:
			embed = discord.Embed(
				title=w.capitalize(),
				description=f"{len([definition for meaning in meanings for definition in meaning['definitions']])} definition(s) found:",
				color=0xBBFFBB
			)
			embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
			count = {}
			truncated = False
			for meaning in meanings:
				if meaning["partOfSpeech"] in count.keys(): count[meaning["partOfSpeech"]] += 1
				else: count[meaning["partOfSpeech"]] = 1
				if len(meaning['definitions']) <= 5:
					definitions = meaning['definitions']
				else:
					definitions = meaning['definitions'][:5]
					truncated = True
				embed.add_field(name=f"{meaning['partOfSpeech'].capitalize()} {count[meaning['partOfSpeech']]}",
					value="\n".join(["- " + definition['definition'] for definition in definitions]))
			if truncated:
				embed.set_footer(text="Some definitons truncated.")
		await ctx.respond(embed=embed, ephemeral=hidden)

	@commands.message_command(name="Get Word Definition")
	async def get_word_definition(self, ctx, message: discord.Message):
		m = message.clean_content[1:] if len(message.clean_content) > 1 and message.clean_content[0] == ';' else message.clean_content
		await self.define(ctx, m, True)

def setup(bot):
	bot.add_cog(Utils(bot))
