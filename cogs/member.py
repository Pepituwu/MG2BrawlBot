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
        if player.id not in bot_data["teams"][team]["members"]:
            bot_data["teams"][team]["members"].append(player.id)
            save_data()
            await interaction.response.send_message(f"✅ {player.mention} ajouté à **{team}**.")
        else:
            await interaction.response.send_message(f"⚠️ Déjà membre.", ephemeral=True)

    @app_commands.command(name="remove_player", description="Admin: Retirer un joueur d'une équipe")
    @app_commands.autocomplete(team=team_autocomplete)
    @app_commands.checks.has_permissions(administrator=True)
    async def remove_player(self, interaction: discord.Interaction, team: str, player: discord.Member):
        if team not in bot_data["teams"]: return
        
        t_data = bot_data["teams"][team]
        if player.id == t_data["leader_id"]:
            await interaction.response.send_message("⛔ On ne peut pas virer le chef.", ephemeral=True)
            return

        if player.id in t_data["members"]:
            t_data["members"].remove(player.id)
            save_data()
            await interaction.response.send_message(f"🚪 {player.mention} retiré de **{team}**.")


async def setup(bot):
    await bot.add_cog(Members(bot))