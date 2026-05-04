import discord
from discord.ext import commands
from discord import app_commands
from utils.data_manager import bot_data, save_data, team_autocomplete

class Members(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="add_player", description="Admin: Ajouter un joueur à une équipe")
    @app_commands.autocomplete(team=team_autocomplete)
    @app_commands.checks.has_permissions(administrator=True)
    async def add_player(self, interaction: discord.Interaction, team: str, player: discord.Member):
        if team not in bot_data["teams"]: return
        
        team_data = bot_data["teams"][team]
        
        # Vérifier si le joueur est déjà dans l'équipe
        if any(m["id"] == player.id for m in team_data["members"]):
            await interaction.response.send_message(f"⚠️ {player.mention} est déjà membre.", ephemeral=True)
            return
        
        # Ajouter le joueur avec sa fortune initiale (0)
        team_data["members"].append({
            "id": player.id,
            "wealth": 0
        })
        save_data()
        await interaction.response.send_message(f"✅ {player.mention} ajouté à **{team}** (Fortune: 0).")

    @app_commands.command(name="remove_player", description="Admin: Retirer un joueur d'une équipe")
    @app_commands.autocomplete(team=team_autocomplete)
    @app_commands.checks.has_permissions(administrator=True)
    async def remove_player(self, interaction: discord.Interaction, team: str, player: discord.Member):
        if team not in bot_data["teams"]: return
        
        t_data = bot_data["teams"][team]
        if player.id == t_data["leader_id"]:
            await interaction.response.send_message("⛔ On ne peut pas virer le chef.", ephemeral=True)
            return

        # Chercher et retirer le joueur
        member_to_remove = next((m for m in t_data["members"] if m["id"] == player.id), None)
        if member_to_remove:
            t_data["members"].remove(member_to_remove)
            save_data()
            await interaction.response.send_message(f"🚪 {player.mention} retiré de **{team}**.")
        else:
            await interaction.response.send_message(f"⚠️ {player.mention} n'est pas membre de **{team}**.", ephemeral=True)

    @app_commands.command(name="add_wealth", description="Modo: Attribuer des points de contribution à un joueur")
    @app_commands.autocomplete(team=team_autocomplete)
    @app_commands.checks.has_permissions(administrator=True)
    async def add_wealth(self, interaction: discord.Interaction, team: str, player: discord.Member, amount: int):
        """Ajoute des points de richesse personnelle au joueur et à la trésorerie de l'équipe"""
        if team not in bot_data["teams"]:
            await interaction.response.send_message("❌ Équipe introuvable.", ephemeral=True)
            return
        
        t_data = bot_data["teams"][team]
        
        # Chercher le joueur
        member = next((m for m in t_data["members"] if m["id"] == player.id), None)
        if not member:
            await interaction.response.send_message(f"⚠️ {player.mention} n'est pas dans **{team}**.", ephemeral=True)
            return
        
        # Ajouter la richesse personnelle et les points l'équipe
        member["wealth"] += amount
        t_data["points"] += amount
        save_data()
        
        embed = discord.Embed(title="💰 Contribution Hebdomadaire", color=discord.Color.gold())
        embed.add_field(name="Joueur", value=player.mention, inline=False)
        embed.add_field(name="Équipe", value=team, inline=False)
        embed.add_field(name="Points attribués", value=f"+ {amount:,} MGP", inline=False)
        embed.add_field(name="Nouvelle fortune personnelle", value=f"**{member['wealth']:,}** MGP", inline=True)
        embed.add_field(name="Nouveau solde équipe", value=f"**{t_data['points']:,}** MGP", inline=True)
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="player_ranking", description="Affiche le classement des joueurs d'une équipe (par fortune personnelle)")
    @app_commands.autocomplete(team=team_autocomplete)
    async def player_ranking(self, interaction: discord.Interaction, team: str):
        """Affiche les joueurs d'une équipe triés par fortune personnelle"""
        if team not in bot_data["teams"]:
            await interaction.response.send_message("❌ Équipe introuvable.", ephemeral=True)
            return
        
        t_data = bot_data["teams"][team]
        
        # Trier les membres par fortune (décroissant)
        sorted_members = sorted(t_data["members"], key=lambda m: m["wealth"], reverse=True)
        
        if not sorted_members:
            await interaction.response.send_message(f"❌ Aucun membre dans **{team}**.", ephemeral=True)
            return
        
        embed = discord.Embed(title=f"🏆 Classement de **{team}**", color=discord.Color.gold())
        embed.description = "Fortune personnelle des joueurs (mise à jour hebdomadaire)"
        
        ranking_text = ""
        for i, member in enumerate(sorted_members, 1):
            user = await interaction.client.fetch_user(member["id"])
            username = user.name if user else f"ID:{member['id']}"
            
            medal = "👑" if member["id"] == t_data["leader_id"] else "•"
            ranking_text += f"{i}. {medal} **{username}** : {member['wealth']:,} MGP\n"
        
        embed.add_field(name="Joueurs", value=ranking_text, inline=False)
        embed.set_footer(text=f"Effectif total: {len(sorted_members)} joueurs")
        
        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(Members(bot))