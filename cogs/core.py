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
	async def start(self, ctx):
		cur = self.con.cursor()
		res = cur.execute("select * from Matches where ChannelId = ? and Ongoing = true;", (ctx.channel_id,))
		if res.fetchone() is None:
			conn = sqlite3.connect("database.db")
			curr = conn.cursor()
			curr.execute("insert into Matches (ChannelId, NextTurnId, Ongoing, DatePlayed, Ranked, TimePlayed) values (?, ?, ?, ?, ?, ?)",
				(ctx.channel_id, 1, True, datetime.date.today().strftime("%Y%m%d"), False, int(datetime.datetime.now().timestamp())))
			match = curr.lastrowid
			curr.execute("insert or ignore into Players (PlayerId, DateJoined) values (?, ?)", (ctx.author.id, datetime.date.today().strftime("%Y%m%d")))
			curr.execute("insert into MatchPlayer (MatchId, PlayerId, PlayerNo, Points, NoWords, RankingChange) values (?,?,?,?,?,null);",
				(match, ctx.author.id, 1, 0, 0))
			conn.commit()
			conn.close()
			await ctx.respond("Match started!")
		else:
			await ctx.respond("Match already ongoing!")

	@commands.slash_command(description="Join an ongoing game in the channel.")
	async def join(self, ctx):
		cur = self.con.cursor()
		res = cur.execute("select MatchId from Matches where ChannelId = ? and Ongoing = true;", (ctx.channel.id,))
		if (fetch:=res.fetchone()) is None:
			await ctx.respond("There isn't an ongoing game in this channel.")
			return

		res2 = cur.execute("""select mp.PlayerId
			from Matches m inner join MatchPlayer mp on m.MatchId = mp.MatchId
			where m.MatchId = ?""", (fetch[0],))
		players = [x[0] for x in res2.fetchall()]

		if ctx.author.id in players:
			await ctx.respond("You are already inside the game.")
			return

		conn = sqlite3.connect("database.db")
		curr = conn.cursor()
		curr.execute("insert or ignore into Players (PlayerId, DateJoined) values (?, ?)", (ctx.author.id, datetime.date.today().strftime("%Y%m%d")))
		curr.execute("insert into MatchPlayer (MatchId, PlayerId, PlayerNo, Points, NoWords, RankingChange) values (?,?,?,?,?,null);",
			(fetch[0], ctx.author.id, len(players) + 1, 0, 0))
		conn.commit()
		conn.close()
		await ctx.respond("Joined.")

	@commands.Cog.listener()
	async def on_message(self, message):
		if message.author.bot:
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

		if fetch[1] is not None and message.clean_content[0] != fetch[1]:
			await message.add_reaction("\N{CROSS MARK}")
			return

		if self.bot.get_cog('Mechanics').define(message.clean_content)[0]:
			res3 = cur.execute("""select *
				from Turns
				where MatchId = ?;""", (fetch[0],))
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
				(int(datetime.datetime.now().timestamp()), fetch2[0], message.clean_content[-1], fetch[0]))
			curr.execute("update MatchPlayer set Points = Points + ?, NoWords = NoWords + 1",
				(self.bot.get_cog('Mechanics').score(message.clean_content),))
			curr.execute("insert into Turns (MatchId, PlayerId, TurnNo, Word) values (?, ?, ?, ?);",
				(fetch[0], fetch[2], res4.fetchone()[0], message.clean_content))
			conn.commit()
			conn.close()
			await message.add_reaction("\N{WHITE HEAVY CHECK MARK}")
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
				cur.execute("""update Matches
					set PreviousTurn = ?
					where MatchId = ?;""",
					(int(datetime.datetime.now().timestamp()), match[0]))
				await self.bot.fetch_channel(match[1]).send(self.bot.fetch_user(match[2]).mention + " was knocked out.")
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