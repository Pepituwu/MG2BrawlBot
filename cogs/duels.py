import discord
from discord.ext import commands
from discord import app_commands
import datetime
from datetime import timedelta
from utils.data_manager import bot_data, save_data, team_autocomplete

# --- MENU DÉROULANT POUR LE MODE DE JEU ---
class GameModeSelect(discord.ui.Select):
    def __init__(self, challenger: str, target: str, wager: int, target_leader_id: int):
        self.challenger = challenger
        self.target = target
        self.wager = wager
        self.target_leader_id = target_leader_id # On passe l'ID du chef ici
        
        options = [
            discord.SelectOption(label="1v1", description="Affrontement classique", emoji="⚔️"),
            discord.SelectOption(label="2v2", description="Combat en duo", emoji="🤝"),
            discord.SelectOption(label="Crew Battle", description="Bataille d'équipes", emoji="🔥"),
            discord.SelectOption(label="Autre", description="Règles personnalisées", emoji="🎲")
        ]
        super().__init__(placeholder="Choisissez le mode de jeu...", options=options)

    async def callback(self, interaction: discord.Interaction):
        # SÉCURITÉ : Seul le chef ciblé peut choisir le mode
        if interaction.user.id != self.target_leader_id:
            await interaction.response.send_message("⛔ Seul le chef de l'équipe défiée peut choisir le mode de jeu !", ephemeral=True)
            return

        mode = self.values[0]
        now = datetime.datetime.now()
        cooldown_end = int((now + timedelta(days=3)).timestamp())

        # 1. Appliquer le cooldown global de 3 jours aux DEUX équipes
        bot_data["teams"][self.challenger]["global_duel_cooldown"] = cooldown_end
        bot_data["teams"][self.target]["global_duel_cooldown"] = cooldown_end

        # 2. Sauvegarder le duel actif pour les modérateurs
        if "duels" not in bot_data:
            bot_data["duels"] = {}
            
        duel_id = str(interaction.message.id)
        bot_data["duels"][duel_id] = {
            "challenger": self.challenger,
            "target": self.target,
            "wager": self.wager,
            "mode": mode,
            "timestamp": now.timestamp()
        }
        save_data()

        # 3. Mise à jour de l'Embed pour annoncer le match officiel
        embed = discord.Embed(title="⚔️ DUEL OFFICIEL ACCEPTÉ !", color=discord.Color.brand_red())
        embed.description = f"Le défi a été accepté par **{self.target}** ! Que le meilleur gagne."
        embed.add_field(name="ID du Duel", value=f"`{duel_id}`", inline=False)
        embed.add_field(name="Challenger", value=f"🛡️ {self.challenger}", inline=True)
        embed.add_field(name="Défenseur", value=f"🛡️ {self.target}", inline=True)
        embed.add_field(name="Mode de jeu", value=f"**{mode}**", inline=False)
        embed.add_field(name="Mise en jeu", value=f"**{self.wager:,} MG**", inline=False)
        embed.set_footer(text="Les modérateurs s'occuperont du transfert d'argent (Commande : /valide_duel).")

        # On supprime le menu déroulant
        await interaction.response.edit_message(content=None, embed=embed, view=None)
        await interaction.channel.send(f"🔔 **Avis aux Modérateurs** : Le duel `{duel_id}` ({self.challenger} vs {self.target}) est officiel ! (Mise: {self.wager:,} MG)")

# --- LA VUE DU DÉFI (BOUTONS) ---
class DuelView(discord.ui.View):
    def __init__(self, challenger: str, target: str, wager: int, penalty: int, target_leader_id: int):
        super().__init__(timeout=86400) # Expire au bout de 24h
        self.challenger = challenger
        self.target = target
        self.wager = wager
        self.penalty = penalty
        self.target_leader_id = target_leader_id

    # Bouton Accepter
    @discord.ui.button(label="Accepter ⚔️", style=discord.ButtonStyle.success)
    async def accept_duel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.target_leader_id:
            await interaction.response.send_message("⛔ Seul le chef de l'équipe défiée peut accepter !", ephemeral=True)
            return
        
        # On remplace les boutons par le menu déroulant, en passant le target_leader_id
        self.clear_items()
        self.add_item(GameModeSelect(self.challenger, self.target, self.wager, self.target_leader_id))
        await interaction.response.edit_message(content="**Chef, choisissez le mode de jeu pour officialiser :**", view=self)

    # Bouton Refuser
    @discord.ui.button(label="Refuser (Pénalité) 🏃", style=discord.ButtonStyle.danger)
    async def decline_duel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.target_leader_id:
            await interaction.response.send_message("⛔ Seul le chef de l'équipe défiée peut refuser !", ephemeral=True)
            return

        now = datetime.datetime.now()
        cooldown_end = int((now + timedelta(days=3)).timestamp())

        # Pénalité
        bot_data["teams"][self.target]["points"] -= self.penalty
        bot_data["teams"][self.challenger]["points"] += self.penalty

        # Cooldown de refus
        if "refused_duels" not in bot_data["teams"][self.target]:
            bot_data["teams"][self.target]["refused_duels"] = {}
        bot_data["teams"][self.target]["refused_duels"][self.challenger] = cooldown_end
        
        save_data()

        embed = discord.Embed(title="🏳️ DÉFI REFUSÉ", color=discord.Color.dark_grey())
        embed.description = f"L'équipe **{self.target}** a refusé le duel contre **{self.challenger}**."
        embed.add_field(name="Pénalité payée", value=f"{self.penalty:,} MG transférés au challenger.", inline=False)
        embed.set_footer(text=f"{self.target} est immunisée contre {self.challenger} pendant 3 jours.")

        await interaction.response.edit_message(embed=embed, view=None)


# --- LE COG ---
class Duels(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # 1. COMMANDE POUR LANCER UN DUEL
    @app_commands.command(name="duel", description="Défier une autre équipe (5% à 15% du plus petit patrimoine)")
    @app_commands.describe(cible="L'équipe que vous voulez défier", pourcentage="Entre 5 et 15")
    @app_commands.autocomplete(cible=team_autocomplete)
    async def duel_command(self, interaction: discord.Interaction, cible: str, pourcentage: int):
        user_id = interaction.user.id
        now_ts = datetime.datetime.now().timestamp()

        challenger = None
        for name, data in bot_data["teams"].items():
            if data["leader_id"] == user_id:
                challenger = name
                break
        
        if not challenger:
            await interaction.response.send_message("⛔ Vous devez être **Chef d'équipe** pour lancer un duel.", ephemeral=True)
            return
        
        if challenger == cible:
            await interaction.response.send_message("❌ Vous ne pouvez pas vous défier vous-même !", ephemeral=True)
            return

        if cible not in bot_data["teams"]:
            await interaction.response.send_message(f"❌ L'équipe **{cible}** n'existe pas.", ephemeral=True)
            return

        if not (5 <= pourcentage <= 15):
            await interaction.response.send_message("❌ Le pourcentage doit être compris entre **5 et 15**.", ephemeral=True)
            return

        chal_cooldown = bot_data["teams"][challenger].get("global_duel_cooldown", 0)
        if chal_cooldown > now_ts:
            await interaction.response.send_message(f"⏳ Votre équipe est en période de repos. Retour possible <t:{chal_cooldown}:R>.", ephemeral=True)
            return

        target_cooldown = bot_data["teams"][cible].get("global_duel_cooldown", 0)
        if target_cooldown > now_ts:
            await interaction.response.send_message(f"⏳ L'équipe {cible} est déjà occupée ou en repos. Dispo <t:{target_cooldown}:R>.", ephemeral=True)
            return

        refused_cooldown = bot_data["teams"][cible].get("refused_duels", {}).get(challenger, 0)
        if refused_cooldown > now_ts:
            await interaction.response.send_message(f"🛡️ L'équipe {cible} a récemment refusé votre défi. Réessayez <t:{refused_cooldown}:R>.", ephemeral=True)
            return

        chal_points = bot_data["teams"][challenger]["points"]
        target_points = bot_data["teams"][cible]["points"]
        plus_petit_patrimoine = min(chal_points, target_points)
        
        wager = int(round(plus_petit_patrimoine * (pourcentage / 100), -2))
        penalty = int(round(plus_petit_patrimoine * 0.02, -2))
        
        # Sécurité supplémentaire au cas où l'équipe est tellement pauvre que l'arrondi donne 0
        if penalty == 0 and plus_petit_patrimoine > 0:
            penalty = 100

        target_leader_id = bot_data["teams"][cible]["leader_id"]

        embed = discord.Embed(title="🥊 DÉFI LANCÉ !", color=discord.Color.orange())
        embed.description = f"Le chef de **{challenger}** provoque **{cible}** en duel !"
        embed.add_field(name="Pourcentage choisi", value=f"{pourcentage}%", inline=True)
        embed.add_field(name="Mise en jeu", value=f"**{wager:,} MG**", inline=True)
        embed.add_field(name="Pénalité de refus (2%)", value=f"**{penalty:,} MG**", inline=False)
        embed.set_footer(text="Seul le chef de l'équipe défiée peut répondre.")

        view = DuelView(challenger, cible, wager, penalty, target_leader_id)
        
        await interaction.response.send_message(f"<@{target_leader_id}>, votre équipe est défiée !", embed=embed, view=view)

    # 2. COMMANDE POUR LISTER LES DUELS
    @app_commands.command(name="list_duels", description="Voir les duels officiels en cours d'attente de résultat")
    async def list_duels(self, interaction: discord.Interaction):
        duels = bot_data.get("duels", {})
        if not duels:
            await interaction.response.send_message("💤 Aucun duel officiel en cours.", ephemeral=True)
            return

        embed = discord.Embed(title="⚔️ Duels en cours", color=discord.Color.red())
        for duel_id, info in duels.items():
            chal = info["challenger"]
            tgt = info["target"]
            mise = info["wager"]
            mode = info["mode"]
            
            embed.add_field(
                name=f"ID : `{duel_id}`", 
                value=f"**{chal}** 🆚 **{tgt}**\nMode: {mode} | Mise: {mise:,} MG", 
                inline=False
            )
            
        await interaction.response.send_message(embed=embed)

    # 3. COMMANDE POUR VALIDER UN DUEL (Admin/Modo)
    @app_commands.command(name="valide_duel", description="Modo: Valider le résultat d'un duel")
    @app_commands.describe(duel_id="L'ID du duel (affiché dans /list_duels)", gagnant="L'équipe qui a gagné le match")
    @app_commands.autocomplete(gagnant=team_autocomplete)
    @app_commands.checks.has_permissions(administrator=True) # Réservé aux admins / modérateurs
    async def valide_duel(self, interaction: discord.Interaction, duel_id: str, gagnant: str):
        duels = bot_data.get("duels", {})
        
        if duel_id not in duels:
            await interaction.response.send_message("❌ Cet ID de duel n'existe pas.", ephemeral=True)
            return
            
        duel = duels[duel_id]
        challenger = duel["challenger"]
        target = duel["target"]
        wager = duel["wager"]

        # Vérifier que le gagnant fait bien partie du duel
        if gagnant not in [challenger, target]:
            await interaction.response.send_message(f"❌ L'équipe **{gagnant}** ne participe pas à ce duel !", ephemeral=True)
            return

        perdant = challenger if gagnant == target else target

        # Transfert d'argent
        bot_data["teams"][gagnant]["points"] += wager
        bot_data["teams"][perdant]["points"] -= wager

        # Suppression du duel de la liste d'attente
        del bot_data["duels"][duel_id]
        save_data()

        # Annonce du résultat
        embed = discord.Embed(title="🏆 RÉSULTAT DU DUEL", color=discord.Color.green())
        embed.description = f"**{gagnant}** a écrasé **{perdant}** et remporte la mise !"
        embed.add_field(name="Gains", value=f"+ {wager:,} MG pour {gagnant}", inline=False)
        embed.add_field(name="Pertes", value=f"- {wager:,} MG pour {perdant}", inline=False)
        embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/3112/3112946.png") # Petite icone de coupe

        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(Duels(bot))