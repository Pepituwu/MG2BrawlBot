import os
import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
from datetime import datetime
from utils import data_manager

API_BASE = "https://api.brawlhalla.com"
class ProfileCog(commands.Cog):
	def __init__(self, bot: commands.Bot):
		self.bot = bot
		self.api_key = os.getenv("BH_API_KEY")

	async def _fetch(self, session: aiohttp.ClientSession, path: str, params: dict | None = None):
		if not self.api_key:
			raise RuntimeError("Clé API Brawlhalla absente")
		params = params or {}
		params["api_key"] = self.api_key
		url = f"{API_BASE}{path}"
		async with session.get(url, params=params) as resp:
			if resp.status == 200:
				return await resp.json()
			text = await resp.text()
			raise ValueError(f"API error {resp.status}: {text}")

	@app_commands.command(name="link_bh", description="Lier votre compte Brawlhalla (steamid64 ou brawlhalla_id)")
	@app_commands.describe(steamid="Steam64 ID", brawlhalla_id="ID Brawlhalla")
	async def link_bh(self, interaction: discord.Interaction, steamid: str | None = None, brawlhalla_id: int | None = None):
		await interaction.response.defer(ephemeral=True)
		if not self.api_key:
			await interaction.followup.send("La variable d'environnement BRAWLHALLA_API_KEY n'est pas définie.", ephemeral=True)
			return
		if not steamid and not brawlhalla_id:
			await interaction.followup.send("Fournissez `steamid` ou `brawlhalla_id`.", ephemeral=True)
			return
		async with aiohttp.ClientSession() as session:
			try:
				if steamid:
					data = await self._fetch(session, "/search", params={"steamid": steamid})
					bh_id = data.get("brawlhalla_id")
					name = data.get("name")
				else:
					bh_id = brawlhalla_id
					data = await self._fetch(session, f"/player/{bh_id}/stats")
					name = data.get("name")
			except RuntimeError:
				await interaction.followup.send("Clé API manquante.", ephemeral=True)
				return
			except ValueError as e:
				await interaction.followup.send(f"Erreur API : {e}", ephemeral=True)
				return
			if not bh_id:
				await interaction.followup.send("Impossible de trouver le compte Brawlhalla.", ephemeral=True)
				return
			dm = data_manager.bot_data
			if "brawlhalla" not in dm:
				dm["brawlhalla"] = {}
			dm["brawlhalla"][str(interaction.user.id)] = {"brawlhalla_id": bh_id, "name": name, "linked_at": datetime.utcnow().isoformat()}
			data_manager.save_data()
			await interaction.followup.send(f"Compte lié : {name} ({bh_id}).", ephemeral=True)

	@app_commands.command(name="unlink_bh", description="Délier votre compte Brawlhalla")
	async def unlink_bh(self, interaction: discord.Interaction):
		await interaction.response.defer(ephemeral=True)
		dm = data_manager.bot_data
		if "brawlhalla" in dm and str(interaction.user.id) in dm["brawlhalla"]:
			del dm["brawlhalla"][str(interaction.user.id)]
			data_manager.save_data()
			await interaction.followup.send("Compte Brawlhalla délié.", ephemeral=True)
		else:
			await interaction.followup.send("Aucun compte lié.", ephemeral=True)

	def _find_team_info(self, discord_id: int):
		dm = data_manager.bot_data
		if "teams" not in dm:
			return None
		for team_name, team in dm["teams"].items():
			members = team.get("members", [])
			team_total = sum(member.get("wealth", 0) for member in members)
			for member in members:
				if member.get("id") == discord_id:
					player_wealth = member.get("wealth", 0)
					percent = 0.0
					if team_total > 0:
						percent = (player_wealth / team_total) * 100
					return {
						"team_name": team_name,
						"player_wealth": player_wealth,
						"team_total": team_total,
						"percent": percent,
					}
		return None

	@app_commands.command(name="get_player_info", description="Obtenir les infos de l'utilisateur: équipe, contribution, pseudo Brawlhalla, peak ELO 1v1 et 2v2")
	@app_commands.describe(member="Membre Discord à afficher (laisser vide pour vous)")
	async def get_player_info(self, interaction: discord.Interaction, member: discord.Member | None = None):
		await interaction.response.defer(ephemeral=True)
		target = member or interaction.user
		dm = data_manager.bot_data
		if "brawlhalla" not in dm or str(target.id) not in dm["brawlhalla"]:
			await interaction.followup.send("Aucun compte Brawlhalla lié pour cet utilisateur.", ephemeral=True)
			return
		entry = dm["brawlhalla"][str(target.id)]
		bh_id = entry["brawlhalla_id"]
		team_info = self._find_team_info(target.id)
		team_name = team_info["team_name"] if team_info else "Aucune équipe"
		contribution = "N/A"
		if team_info:
			contribution = f"{team_info['player_wealth']} MGP ({team_info['percent']:.1f}%)"
		async with aiohttp.ClientSession() as session:
			try:
				ranked = await self._fetch(session, f"/player/{bh_id}/ranked")
			except Exception as e:
				await interaction.followup.send(f"Erreur en récupérant les données : {e}", ephemeral=True)
				return
		peak_1v1 = ranked.get("peak_rating", "N/A")
		peak_2v2 = "N/A"
		teams_2v2 = ranked.get("2v2", []) or []
		if isinstance(teams_2v2, list) and teams_2v2:
			best_2v2 = max((team.get("peak_rating", 0) for team in teams_2v2 if isinstance(team, dict)), default=0)
			peak_2v2 = best_2v2 if best_2v2 > 0 else "N/A"
		embed = discord.Embed(
			title=f"Infos Brawlhalla - {target.display_name}",
			color=0x00ffcc,
			timestamp=datetime.utcnow()
		)
		embed.add_field(name="Équipe", value=team_name, inline=False)
		embed.add_field(name="Contribution", value=contribution, inline=False)
		embed.add_field(name="Pseudo Brawlhalla", value=entry.get("name", "N/A"), inline=False)
		embed.add_field(name="Peak ELO 1v1", value=str(peak_1v1), inline=True)
		embed.add_field(name="Peak ELO 2v2", value=str(peak_2v2), inline=True)
		embed.set_footer(text="Informations récupérées depuis l'API Brawlhalla")
		await interaction.followup.send(embed=embed, ephemeral=True)

	@app_commands.command(name="show_bh", description="Afficher le compte Brawlhalla lié")
	async def show_bh(self, interaction: discord.Interaction):
		await interaction.response.defer(ephemeral=True)
		dm = data_manager.bot_data
		if "brawlhalla" not in dm or str(interaction.user.id) not in dm["brawlhalla"]:
			await interaction.followup.send("Aucun compte lié. Utilisez /link_bh.", ephemeral=True)
			return
		entry = dm["brawlhalla"][str(interaction.user.id)]
		bh_id = entry["brawlhalla_id"]
		async with aiohttp.ClientSession() as session:
			try:
				ranked = await self._fetch(session, f"/player/{bh_id}/ranked")
			except Exception as e:
				await interaction.followup.send(f"Erreur en récupérant les données : {e}", ephemeral=True)
				return
		rating = ranked.get("rating", "N/A")
		tier = ranked.get("tier", "N/A")
		peak = ranked.get("peak_rating", "N/A")
		embed = discord.Embed(
			title=f"Compte Brawlhalla lié - {interaction.user.display_name}",
			color=0x00ffcc,
			timestamp=datetime.utcnow()
		)
		embed.add_field(name="Pseudo Brawlhalla", value=entry.get("name", "N/A"), inline=False)
		embed.add_field(name="ID Brawlhalla", value=str(bh_id), inline=False)
		embed.add_field(name="Rating 1v1", value=str(rating), inline=True)
		embed.add_field(name="Tier 1v1", value=str(tier), inline=True)
		embed.add_field(name="Peak 1v1", value=str(peak), inline=False)
		embed.set_footer(text="Informations récupérées depuis l'API Brawlhalla")
		await interaction.followup.send(embed=embed, ephemeral=True)

async def setup(bot: commands.Bot):
	await bot.add_cog(ProfileCog(bot))

