import discord
from discord.ext import commands
from discord import app_commands

class General(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # --- COMMANDE !SYNC ---
    @commands.command()
    async def sync(self, ctx):
        synced = await self.bot.tree.sync()
        await ctx.send(f"✅ Synchro effectuée : {len(synced)} commandes slash sont actives.")

    # --- COMMANDE /PING ---
    @app_commands.command(name="ping", description="Vérifier la latence du bot")
    async def ping(self, interaction: discord.Interaction):
        latency = round(self.bot.latency * 1000)
        await interaction.response.send_message(f"Pong! 🏓 ({latency}ms)")

    # --- COMMANDE /HELP (Mise à jour avec les duels) ---
    @app_commands.command(name="help", description="Affiche la liste des commandes et le mode d'emploi")
    async def help_command(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="📚 Aide - Brawlhalla Clan Manager",
            description="Bienvenue sur le bot de gestion de clan, de mercato et de duels.",
            color=discord.Color.blurple()
        )

        # --- 1. SECTION PUBLIQUE & MERCATO ---
        public_cmds = (
            "� **`/ping`** : Vérifier la latence du bot.\n"
            "🏆 **`/get_teams`** : Voir le classement, les chefs et les soldes.\n"
            "🛡️ **`/team_info [équipe]`** : Détails d'une équipe.\n"
            "🔨 **`/get_auctions`** : Voir toutes les enchères en cours.\n"
            "🔎 **`/auction_info [joueur]`** : Trouver l'enchère d'un joueur spécifique.\n"
            "💎 **`/team_ranking`** : Classement des équipes par fortune."
            "👑 **`/global_ranking`** : Classement des joueurs par fortune personnelle."
        )
        embed.add_field(name="🌍 Commandes Générales", value=public_cmds, inline=False)

        # --- 2. SECTION DUELS ---
        duel_cmds = (
            "🥊 **`/duel [cible] [%]`** : Défier une équipe (Mise : 5 à 15% du plus petit patrimoine).\n"
            "⚔️ **`/list_duels`** : Voir les duels officiels en attente de résultat.\n\n"
            "*Règles des duels :*\n"
            "• Le chef défié peut **Accepter** (choix du mode de jeu) ou **Refuser** (Pénalité de 2% de la mise transférée au challenger).\n"
            "• Un refus immunise l'équipe ciblée pendant 3 jours contre l'attaquant.\n"
            "• Un duel accepté bloque les deux équipes (cooldown global de 3 jours)."
        )
        embed.add_field(name="🥊 Système de Duels", value=duel_cmds, inline=False)

        # --- 3. FONCTIONNEMENT DES ENCHÈRES ---
        auction_help = (
            "• **Seuls les Chefs** peuvent utiliser les boutons (+1000, +2000...).\n"
            "• L'ancien meneur reçoit un MP s'il se fait surenchérir.\n"
            "• Le transfert et le paiement sont automatiques à la fin du chrono."
        )
        embed.add_field(name="💡 Comment enchérir ?", value=auction_help, inline=False)

        # --- 3.5 SECTION FORTUNE PERSONNELLE ---
        wealth_cmds = (
            "💎 **`/player_ranking [équipe]`** : Classement des joueurs par fortune personnelle.\n"
        )
        embed.add_field(name="👑 Richesse Personnelle", value=wealth_cmds, inline=False)

        # --- 4. SECTION BRAWLHALLA ---
        bh_cmds = (
            "🎮 **`/link_bh [brawlhalla_id]`** : Lier votre compte Brawlhalla au serveur.\n"
            "🔓 **`/unlink_bh`** : Délier votre compte Brawlhalla.\n"
            "📊 **`/show_bh`** : Afficher votre compte Brawlhalla lié (Rating, Tier, Peak).\n"
            "👤 **`/get_player_info [membre]`** : Afficher les infos complètes d'un joueur (équipe, contribution, Peak ELO 1v1 et 2v2)."
        )
        embed.add_field(name="🎮 Comptes Brawlhalla", value=bh_cmds, inline=False)

        # --- 5. SECTION ÉVÉNEMENTS ---
        event_cmds = (
            "🎪 **`/create_event`** : Créer un nouvel événement (Admin seulement)\n"
            "📋 **`/list_events`** : Lister les événements actifs\n"
            "🗑️ **`/cancel_event [event_id]`** : Annuler un événement (Admin seulement)\n\n"
            "*Comment ça marche :*\n"
            "• Les admins créent des événements avec une récompense en MGP\n"
            "• Les membres s'inscrivent via les boutons sous l'embed\n"
            "• L'admin termine l'event et désigne le gagnant\n"
            "• Le gagnant reçoit la récompense (similaire à /add_wealth)\n"
            "• Les admins peuvent annuler les events avec leur ID"
        )
        embed.add_field(name="🎉 Système d'Événements", value=event_cmds, inline=False)

        # --- 6. SECTION ADMIN ---
        if interaction.user.guild_permissions.administrator:
            admin_cmds = (
                "`/add_team` | `/remove_teams` : Gestion des équipes\n"
                "`/add_auction` : Mettre un joueur aux enchères\n"
                "`/valide_duel` : Valider le gagnant d'un duel officiel\n"
                "`/cancel_duel` : Annuler un duel sans pénalité\n"
                "`/add_wealth [équipe] [joueur] [montant]` : Attribuer des points de contribution hebdo\n"
                "`/add_points` | `/remove_points` : Gestion de la banque\n"
                "`/add_player` | `/remove_player` : Transferts forcés"
            )
            embed.add_field(name="👮 Espace Administrateur", value=admin_cmds, inline=False)

        embed.set_footer(text="Bot développé pour la communauté Brawlhalla")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(General(bot))