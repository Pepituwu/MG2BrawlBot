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
        member_index_to_remove = -1
        for i, m_entry in enumerate(t_data["members"]):
            if isinstance(m_entry, dict):
                if m_entry.get("id") == player.id:
                    member_index_to_remove = i
                    break
            elif isinstance(m_entry, (int, float)):
                if int(m_entry) == player.id:
                    member_index_to_remove = i
                    break

        if member_index_to_remove != -1:
            del t_data["members"][member_index_to_remove]
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
        member_obj = None
        for i, m_entry in enumerate(t_data["members"]):
            if isinstance(m_entry, dict):
                if m_entry.get("id") == player.id:
                    member_obj = m_entry
                    break
            elif isinstance(m_entry, (int, float)):
                if int(m_entry) == player.id:
                    member_obj = {"id": int(m_entry), "wealth": 0}
                    t_data["members"][i] = member_obj # Update in-place
                    break

        member = member_obj
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
        # Gérer les anciennes entrées où les membres sont des IDs entiers
        def get_member_wealth(member_entry):
            if isinstance(member_entry, dict):
                return member_entry.get("wealth", 0)
            elif isinstance(member_entry, (int, float)):
                return 0  # Les anciens IDs entiers ont une fortune de 0 par défaut
            return 0 # Cas par défaut si autre type inattendu

        sorted_members = sorted(t_data["members"], key=get_member_wealth, reverse=True)
        
        if not sorted_members:
            await interaction.response.send_message(f"❌ Aucun membre dans **{team}**.", ephemeral=True)
            return
        
        embed = discord.Embed(title=f"🏆 Classement de **{team}**", color=discord.Color.gold())
        embed.description = "Fortune personnelle des joueurs (mise à jour hebdomadaire)"
        
        ranking_text = ""
        for i, member_entry in enumerate(sorted_members, 1):
            if isinstance(member_entry, (int, float)):
                member_entry = {"id": int(member_entry), "wealth": 0}

            user = await interaction.client.fetch_user(member_entry["id"])
            username = user.name if user else f"ID:{member_entry['id']}"
            
            medal = "👑" if member_entry["id"] == t_data["leader_id"] else "•"
            ranking_text += f"{i}. {medal} **{username}** : {member_entry['wealth']:,} MGP\n"
        
        embed.add_field(name="Joueurs", value=ranking_text, inline=False)
        embed.set_footer(text=f"Effectif total: {len(sorted_members)} joueurs")
        
        await interaction.response.send_message(embed=embed)

    # --- GLOBAL RANKING --- 
    @app_commands.command(name="global_ranking", description="Affiche le classement global de tous les joueurs (par fortune personnelle)")
    async def global_ranking(self, interaction: discord.Interaction):
        """Affiche tous les joueurs de toutes les équipes triés par fortune personnelle"""
        all_members = []
        for team_name, team in bot_data.get("teams", {}).items():
            for member in team.get("members", []):
                if isinstance(member, dict):
                    all_members.append({
                        "id": member["id"],
                        "wealth": member.get("wealth", 0),
                        "team": team_name
                    })
        
        sorted_members = sorted(all_members, key=lambda m: m["wealth"], reverse=True)
        
        if not sorted_members:
            await interaction.response.send_message("❌ Aucun joueur trouvé.", ephemeral=True)
            return
        
        # Initialiser l'embed
        embed = discord.Embed(title="🌍 Classement Global des Joueurs", color=discord.Color.blue())
        embed.description = "Fortune personnelle de tous les joueurs"

        # Nombre maximum de caractères par champ d'embed
        MAX_FIELD_LENGTH = 1024
        
        ranking_text = ""
        field_count = 0

        for i, member in enumerate(sorted_members, 1):
            user = await interaction.client.fetch_user(member["id"])
            username = user.name if user else f"ID:{member['id']}"
            
            # Formatage de l'entrée du joueur
            member_line = f"{i}. **{username}** | {member['team']} : {member['wealth']:,} MGP\n"
            
            # Vérifier si l'ajout de la ligne actuelle dépasse la limite de caractères
            if len(ranking_text) + len(member_line) > MAX_FIELD_LENGTH and ranking_text != "":
                # Ajouter le champ actuel et en commencer un nouveau
                embed.add_field(name=f"Joueurs (suite {field_count + 1})", value=ranking_text, inline=False)
                ranking_text = ""
                field_count += 1
            
            ranking_text += member_line
            
        # Ajouter le dernier champ si ranking_text n'est pas vide
        if ranking_text:
            embed.add_field(name=f"Joueurs (suite {field_count + 1})" if field_count > 0 else "Joueurs", value=ranking_text, inline=False)

        embed.set_footer(text=f"Total: {len(sorted_members)} joueurs")
        
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Members(bot))