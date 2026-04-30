import discord
from discord.ext import commands
from discord import app_commands
from utils.data_manager import bot_data, save_data, team_autocomplete

class Teams(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="add_team", description="Admin: Créer une nouvelle équipe")
    @app_commands.describe(nom="Le nom de l'équipe", chef="Le leader", points="Budget de départ")
    @app_commands.checks.has_permissions(administrator=True)
    async def add_team(self, interaction: discord.Interaction, nom: str, chef: discord.Member, points: int = 100000):
        # Ici on garde 'nom' car c'est une création, pas une recherche
        if nom in bot_data["teams"]:
            await interaction.response.send_message(f"❌ L'équipe **{nom}** existe déjà !", ephemeral=True)
            return
        
        bot_data["teams"][nom] = {
            "leader_id": chef.id,
            "points": points,
            "members": [
                {
                    "id": chef.id,
                    "wealth": 0
                }
            ],
            "created_at": str(interaction.created_at)
        }
        save_data()
        
        embed = discord.Embed(title="✅ Nouvelle Équipe Créée", color=discord.Color.green())
        embed.add_field(name="Nom", value=nom)
        embed.add_field(name="Leader", value=chef.mention)
        embed.add_field(name="Solde", value=f"{points:,} MGP")
        await interaction.response.send_message(embed=embed)

    # --- COMMANDE GET_TEAMS ---
    @app_commands.command(name="get_teams", description="Affiche la liste de toutes les équipes enregistrées")
    async def get_teams(self, interaction: discord.Interaction):
        teams = bot_data.get("teams", {})
        if not teams:
            await interaction.response.send_message("❌ Aucune équipe.", ephemeral=True)
            return

        embed = discord.Embed(title="🏆 Équipes", color=discord.Color.blue())
        for name, info in teams.items():
            member_count = len(info['members'])
            details = f"👑 <@{info['leader_id']}>\n💰 {info['points']:,} MGP\n👥 {member_count}"
            embed.add_field(name=f"🛡️ {name}", value=details, inline=True)
        await interaction.response.send_message(embed=embed)

    # --- COMMANDE TEAM_INFO (Correction de l'erreur ici) ---
    @app_commands.command(name="team_info", description="Détails d'une équipe")
    @app_commands.describe(team="Le nom de l'équipe à chercher")
    @app_commands.autocomplete(team=team_autocomplete) # On utilise 'team' ici
    async def team_info(self, interaction: discord.Interaction, team: str): # ET on utilise 'team' ici aussi !
        
        # Note : La variable s'appelle 'team' maintenant, plus 'nom'
        team_data = bot_data["teams"].get(team)
        
        if not team_data:
            await interaction.response.send_message(f"❌ L'équipe **{team}** est introuvable.", ephemeral=True)
            return

        leader_id = team_data.get("leader_id")
        points = team_data.get("points", 0)
        members = team_data.get("members", [])
        created_at = team_data.get("created_at", "Date inconnue")

        members_list_text = ""
        for member in members:
            # Gérer l'ancienne structure (simple ID) et la nouvelle (dict avec id et wealth)
            if isinstance(member, dict):
                member_id = member.get("id")
                wealth = member.get("wealth", 0)
            else:
                member_id = member
                wealth = 0
            
            if member_id == leader_id:
                members_list_text += f"👑 <@{member_id}> | Fort: {wealth:,} MGP\n"
            else:
                members_list_text += f"👤 <@{member_id}> | Fort: {wealth:,} MGP\n"

        if not members_list_text:
            members_list_text = "Aucun membre"

        embed = discord.Embed(title=f"🛡️ Fiche d'équipe : {team}", color=discord.Color.gold())
        embed.add_field(name="💰 Trésorerie", value=f"**{points:,}** MGP", inline=True)
        embed.add_field(name="👑 Leader", value=f"<@{leader_id}>", inline=True)
        
        date_display = created_at.split(" ")[0] if " " in created_at else created_at
        embed.add_field(name="📅 Création", value=date_display, inline=True)
        embed.add_field(name=f"👥 Effectif ({len(members)})", value=members_list_text, inline=False)

        await interaction.response.send_message(embed=embed)

    # --- COMMANDE REMOVE_TEAM ---
    @app_commands.command(name="remove_teams", description="Admin: Supprimer une équipe")
    @app_commands.describe(team="L'équipe à supprimer")
    @app_commands.autocomplete(team=team_autocomplete)
    @app_commands.checks.has_permissions(administrator=True)
    async def remove_teams(self, interaction: discord.Interaction, team: str):
        if team in bot_data["teams"]:
            del bot_data["teams"][team]
            save_data()
            await interaction.response.send_message(f"🗑️ L'équipe **{team}** a été supprimée.")
        else:
            await interaction.response.send_message("❌ Équipe introuvable.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Teams(bot))