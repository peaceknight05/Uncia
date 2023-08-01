import discord
import datetime
import sqlite3
from discord.ext import commands, tasks

class Core(commands.Cog):
	def __init__(self, bot):
		self.bot = bot
		self.con = sqlite3.connect("database.db")
		self.conAbort = sqlite3.connect("database.db")
		self.conOver = sqlite3.connect("database.db")
		self.checkGameAbort.start()
		self.checkGameOver.start()

	def cog_unload(self):
		self.checkGameAbort.stop()
		self.checkGameOver.stop()
		self.con.close()
		self.conAbort.close()
		self.conOver.close()

	@commands.slash_command(description="Starts a Word Chain match.")
	@commands.guild_only()
	async def start(self, ctx):
		cur = self.con.cursor()
		res = cur.execute("select * from Matches where ChannelId = ? and Ongoing = true;", (ctx.channel_id,))
		if res.fetchone() is None:
			conn = sqlite3.connect("database.db")
			curr = conn.cursor()
			curr.execute("insert into Matches (ChannelId, NextTurnId, Ongoing, DatePlayed, Ranked, TimePlayed, ServerId) values (?, ?, ?, ?, ?, ?, ?)",
				(ctx.channel_id, 1, True, datetime.date.today().strftime("%Y%m%d"), False, int(datetime.datetime.now().timestamp()), ctx.guild_id))
			match = curr.lastrowid
			curr.execute("insert or ignore into Players (PlayerId, DateJoined) values (?, ?)", (ctx.author.id, datetime.date.today().strftime("%Y%m%d")))
			curr.execute("insert into MatchPlayer (MatchId, PlayerId, PlayerNo, Points, NoWords, RankingChange) values (?,?,?,?,?,null);",
				(match, ctx.author.id, 1, 0, 0))
			conn.commit()
			conn.close()
			embed = discord.Embed(title="Match started!", fields=[
				discord.EmbedField("Ranked", "No", inline=True),
				discord.EmbedField("Time Control", "10 seconds", inline=True)
			], color=0x88EE88,
			timestamp=datetime.datetime.now())
			embed.set_footer(text="Game will abort in 60 seconds if no second player joins.")
			embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
			await ctx.respond(embed=embed)
			embed2 = discord.Embed(title=f"{ctx.author.display_name}'s turn!", fields=[
				discord.EmbedField("Previous Word", "-")
			], color=ctx.author.color,
			timestamp=datetime.datetime.now())
			embed2.set_footer(text="Turn 1")
			embed2.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
			await ctx.channel.send(embed=embed2)
		else:
			await ctx.respond("Match already ongoing!")

	@commands.slash_command(description="Join an ongoing game in the channel.")
	@commands.guild_only()
	async def join(self, ctx):
		cur = self.con.cursor()
		res = cur.execute("select MatchId from Matches where ChannelId = ? and Ongoing = true;", (ctx.channel.id,))
		if (fetch:=res.fetchone()) is None:
			embed = discord.Embed(
				title="Error",
				description="There isn't an ongoing game in this channel.",
				color=0xFF8888,
				timestamp=datetime.datetime.now()
			)
			embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
			await ctx.respond(embed=embed, ephemeral=True)
			return

		res2 = cur.execute("""select mp.PlayerId
			from Matches m inner join MatchPlayer mp on m.MatchId = mp.MatchId
			where m.MatchId = ?""", (fetch[0],))
		players = [x[0] for x in res2.fetchall()]

		if ctx.author.id in players:
			embed = discord.Embed(
				title="Error",
				description="You are already inside the game.",
				color=0xFF8888,
				timestamp=datetime.datetime.now()
			)
			embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
			await ctx.respond(embed=embed, ephemeral=True)
			return

		conn = sqlite3.connect("database.db")
		curr = conn.cursor()
		curr.execute("insert or ignore into Players (PlayerId, DateJoined) values (?, ?)", (ctx.author.id, datetime.date.today().strftime("%Y%m%d")))
		curr.execute("insert into MatchPlayer (MatchId, PlayerId, PlayerNo, Points, NoWords, RankingChange) values (?,?,?,?,?,null);",
			(fetch[0], ctx.author.id, len(players) + 1, 0, 0))
		conn.commit()
		conn.close()
		embed = discord.Embed(
			title="Success",
			description=f"{ctx.author.display_name} joined.",
			color=0x88EE88,
			timestamp=datetime.datetime.now()
		)
		embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
		await ctx.respond(embed=embed)

	@commands.Cog.listener()
	async def on_message(self, message):
		if message.author.bot:
			return

		if len(message.clean_content) == 0 or message.clean_content[0] != ';':
			return

		cur = self.con.cursor()
		res = cur.execute("select * from Matches where ChannelId = ? and Ongoing = true;", (message.channel.id,))
		if res.fetchone() is None:
			return

		res = cur.execute("""select m.MatchId, m.LastLetter, mp.PlayerId
			from Matches m inner join MatchPlayer mp on m.MatchId = mp.MatchId and m.NextTurnId = mp.PlayerNo
			where mp.PlayerId = ? and m.ChannelId = ? and m.Ongoing = true;""", (message.author.id, message.channel.id))
		if (fetch:=res.fetchone()) is None:
			await message.add_reaction('\N{RAISED HAND WITH FINGERS SPLAYED}')
			return

		res2 = cur.execute("""select count(*)
			from Matches m inner join MatchPlayer mp on m.MatchId = mp.MatchId
			group by m.MatchId
			having m.MatchId = ? and mp.PlayerNo is not null""",
			(fetch[0],))
		fetch2 = res2.fetchone()
		if fetch2[0] == 1:
			await message.add_reaction('\N{RAISED HAND WITH FINGERS SPLAYED}')
			await message.add_reaction('\N{DIGIT ONE}\N{COMBINING ENCLOSING KEYCAP}')
			await message.add_reaction('\N{NEGATIVE SQUARED LATIN CAPITAL LETTER P}')
			return

		word = message.clean_content.lower()[1:]

		if fetch[1] is not None and word[0] != fetch[1]:
			await message.add_reaction("\N{CROSS MARK}")
			return

		if self.bot.get_cog('Mechanics').define(word)[0]:
			res3 = cur.execute("""select *
				from Turns
				where MatchId = ? and Word = ?;""", (fetch[0], word))
			if (res3.fetchone()) is not None:
				await message.add_reaction("\N{ANTICLOCKWISE DOWNWARDS AND UPWARDS OPEN CIRCLE ARROWS}")
				return

			res4 = cur.execute("""select sum(NoWords)
				from MatchPlayer
				group by MatchId
				having MatchId = ?;""", (fetch[0],))

			conn = sqlite3.connect("database.db")
			curr = conn.cursor()
			curr.execute("""update Matches
				set PreviousTurn = ?, NextTurnId = NextTurnId % ? + 1, LastLetter = ?
				where MatchId = ?;""",
				(int(datetime.datetime.now().timestamp()), fetch2[0], word[-1], fetch[0]))
			curr.execute("update MatchPlayer set Points = Points + ?, NoWords = NoWords + 1 where MatchId = ? and PlayerId = ?",
				(self.bot.get_cog('Mechanics').score(word), fetch[0], fetch[2]))
			curr.execute("insert into Turns (MatchId, PlayerId, TurnNo, Word) values (?, ?, ?, ?);",
				(fetch[0], fetch[2], res4.fetchone()[0], word))
			conn.commit()
			conn.close()
			await message.add_reaction("\N{WHITE HEAVY CHECK MARK}")
			res5 = cur.execute("""select mp.PlayerId
				from MatchPlayer mp, Match m
				where mp.MatchId = m.MatchId and m.MatchId = ? and mp.PlayerNo = m.NextTurnId;""", (fetch[0],))
			res6 = cur.execute("""select Word, TurnNo
				from Turns
				where MatchId = ?
				order by TurnNo desc;""", (fetch[0],))
			fetch6 = res6.fetchone()
			user = await self.bot.fetch_user(res5.fetchone()[0])
			channel = await self.bot.fetch_channel(message.channel.id)
			embed = discord.Embed(title=f"{user.display_name}'s turn!", fields=[
				discord.EmbedField("Previous Word", fetch6[0])
			], color=user.color,
			timestamp=datetime.datetime.now())
			embed.set_footer(text=f"Turn {fetch6[1]}")
			embed.set_author(name=user.display_name, icon_url=user.display_avatar.url)
			await channel.send(embed=embed)
		else:
			await message.add_reaction("\N{NO ENTRY SIGN}")

	@tasks.loop(seconds=1.0)
	async def checkGameOver(self):
		cur = self.conOver.cursor()
		res = cur.execute("""select m.MatchId, m.ChannelId, mp.PlayerId, mp.PlayerNo
			from Matches m inner join MatchPlayer mp on m.MatchId = mp.MatchId and m.NextTurnId = mp.PlayerNo
			where m.Ongoing = true and m.PreviousTurn is not null and m.PreviousTurn < ?;""",
			(int(datetime.datetime.now().timestamp()) - 10,))
		fetch = res.fetchall()
		if fetch is None:
			return
		for match in fetch:
			cur.execute("update MatchPlayer set PlayerNo = PlayerNo - 1 where MatchId = ? and PlayerNo > ?;",
				(match[0], match[3]))
			cur.execute("update MatchPlayer set PlayerNo = null where MatchId = ? and PlayerId = ?;",
				(match[0], match[2]))
			self.conOver.commit()
			res2 = cur.execute("""select mp.PlayerId
				from Matches m inner join MatchPlayer mp on m.MatchId = mp.MatchId
				where m.MatchId = ? and mp.PlayerNo is not null;""", (match[0],))
			if len(fetch2:=res2.fetchall()) == 1:
				cur.execute("update Matches set Ongoing = false where MatchId = ?;", (match[0],))
				user = await self.bot.fetch_user(match[2])
				channel = await self.bot.fetch_channel(match[1])
				await channel.send(user.mention + " was knocked out.")
				winner = await self.bot.fetch_user(fetch2[0][0])
				await channel.send(f"{winner.mention} wins!")
			else:
				res2 = cur.execute("""select count(*)
					from Matches m inner join MatchPlayer mp on m.MatchId = mp.MatchId
					group by m.MatchId
					having m.MatchId = ? and mp.PlayerNo is not null""", (match[0],))
				cur.execute("""update Matches
					set PreviousTurn = ?, NextTurnId = NextTurnId % ?
					where MatchId = ?;""",
					(int(datetime.datetime.now().timestamp()), res2.fetchone()[0], match[0]))
				user = await self.bot.fetch_user(match[2])
				channel = await self.bot.fetch_channel(match[1])
				await channel.send(user.mention + " was knocked out.")
				res3 = cur.execute("""select mp.PlayerId
					from MatchPlayer mp, Match m
					where mp.MatchId = m.MatchId and m.MatchId = ? and mp.PlayerNo = m.NextTurnId;""", (match[0],))
				user = await self.bot.fetch_user(res3.fetchone()[0])
				res4 = cur.execute("""select Word, TurnNo
					from Turns
					where MatchId = ?
					order by TurnNo desc;""", (fetch[0],))
				fetch4 = res4.fetchone()
				embed = discord.Embed(title=f"{user.display_name}'s turn!", fields=[
					discord.EmbedField("Previous Word", fetch4[0])
				], color=user.color,
				timestamp=datetime.datetime.now())
				embed.set_footer(text=f"Turn {fetch4[1]}")
				embed.set_author(name=user.display_name, icon_url=user.display_avatar.url)
				await channel.send(embed=embed)
			self.conOver.commit()

	@tasks.loop(seconds=1.0)
	async def checkGameAbort(self):
		cur = self.conAbort.cursor()
		res = cur.execute("""select m.MatchId, m.ChannelId, m.TimePlayed, count(mp.MatchId) as PlayerCount
			from Matches m inner join MatchPlayer mp on m.MatchId = mp.MatchId
			group by m.MatchId
			having m.Ongoing = true and m.PreviousTurn is null and m.TimePlayed < ? and PlayerCount = 1;""",
			(int(datetime.datetime.now().timestamp()) - 60,))
		fetch = res.fetchall()
		if fetch is None:
			return
		for match in fetch:
			cur.execute("delete from MatchPlayer where MatchId = ?;",
				(match[0],))
			cur.execute("delete from Matches where MatchId = ?;",
				(match[0],))
			channel = await self.bot.fetch_channel(match[1])
			await channel.send("Game aborted.")
			self.conAbort.commit()

def setup(bot):
	bot.add_cog(Core(bot))