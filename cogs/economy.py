import discord
from discord.ext import commands
from discord import app_commands
from utils.data_manager import bot_data, save_data, team_autocomplete

class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="add_points", description="Admin: Ajouter des points à une équipe")
    @app_commands.autocomplete(team=team_autocomplete)
    @app_commands.checks.has_permissions(administrator=True)
    async def add_points(self, interaction: discord.Interaction, team: str, amount: int):
        if team not in bot_data["teams"]:
            return await interaction.response.send_message("❌ Équipe inconnue.", ephemeral=True)
        
        bot_data["teams"][team]["points"] += amount
        save_data()
        await interaction.response.send_message(f"📈 **{team}** : +{amount:,} MGP")

    @app_commands.command(name="remove_points", description="Admin: Retirer des points à une équipe")
    @app_commands.autocomplete(team=team_autocomplete)
    @app_commands.checks.has_permissions(administrator=True)
    async def remove_points(self, interaction: discord.Interaction, team: str, amount: int):
        if team not in bot_data["teams"]:
            return await interaction.response.send_message("❌ Équipe inconnue.", ephemeral=True)
        
        bot_data["teams"][team]["points"] -= amount
        save_data()
        await interaction.response.send_message(f"📉 **{team}** : -{amount:,} MGP")

async def setup(bot):
    await bot.add_cog(Economy(bot))