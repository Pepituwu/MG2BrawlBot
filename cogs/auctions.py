import discord
from discord.ext import commands, tasks
from discord import app_commands
import datetime
from datetime import timedelta
from utils.data_manager import bot_data, save_data

# --- LA VUE (BOUTONS) ---
class AuctionView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    async def process_bid(self, interaction: discord.Interaction, increment: int):
        auction_id = str(interaction.message.id)
        if auction_id not in bot_data["auctions"]:
            await interaction.response.send_message("❌ Cette enchère est terminée ou n'existe plus.", ephemeral=True)
            return

        auction = bot_data["auctions"][auction_id]
        user_id = interaction.user.id

        # Identifier l'équipe du joueur qui clique
        team_name = None
        for name, data in bot_data["teams"].items():
            if data["leader_id"] == user_id:
                team_name = name
                break
        
        if not team_name:
            await interaction.response.send_message("⛔ Seuls les **Chefs d'équipe** peuvent enchérir !", ephemeral=True)
            return

        # Vérifier l'argent
        current_price = auction["current_price"]
        new_price = current_price + increment
        team_balance = bot_data["teams"][team_name]["points"]

        if team_balance < new_price:
            await interaction.response.send_message(f"💸 Fonds insuffisants ! Il vous faut {new_price:,} MGP.", ephemeral=True)
            return

        # --- SAUVEGARDE DE L'ANCIEN MENEUR ---
        ancien_meneur_team = auction.get("highest_bidder")

        # Mise à jour
        auction["current_price"] = new_price
        auction["highest_bidder"] = team_name
        save_data()

        # Visuel de l'enchère publique
        embed = interaction.message.embeds[0]
        embed.set_field_at(1, name="💰 Offre actuelle", value=f"**{new_price:,} MGP**", inline=True)
        embed.set_field_at(2, name="🏆 Meneur", value=f"**{team_name}** (<@{user_id}>)", inline=True)
        
        await interaction.response.edit_message(embed=embed)
        await interaction.followup.send(f"✅ **{team_name}** a enchéri à {new_price:,} MGP !", ephemeral=True)

        # --- SYSTÈME DE NOTIFICATION EN MESSAGE PRIVÉ ---
        # Si un ancien meneur existait ET que ce n'est pas la même équipe qui renchérit
        if ancien_meneur_team and ancien_meneur_team != team_name:
            ancien_leader_id = bot_data["teams"][ancien_meneur_team]["leader_id"]
            try:
                ancien_leader = interaction.client.get_user(ancien_leader_id)
                if not ancien_leader:
                    ancien_leader = await interaction.client.fetch_user(ancien_leader_id)
                
                # Lien pour retourner direct sur l'enchère
                jump_url = f"https://discord.com/channels/{interaction.guild_id}/{interaction.channel_id}/{auction_id}"
                
                dm_embed = discord.Embed(title="⚠️ Alerte Surenchère !", color=discord.Color.red())
                dm_embed.description = f"L'équipe **{team_name}** vient de surenchérir sur une enchère que vous meniez !"
                dm_embed.add_field(name="Nouvelle offre", value=f"**{new_price:,} MGP**", inline=False)
                dm_embed.add_field(name="Riposte", value=f"[🔗 Cliquez ici pour retourner à l'enchère]({jump_url})", inline=False)
                
                # On envoie le MP
                await ancien_leader.send(embed=dm_embed)
            
            except discord.Forbidden:
                # Cette erreur arrive si l'ancien chef a bloqué les messages privés du serveur
                print(f"Impossible d'envoyer un MP à {ancien_leader_id} (MP bloqués)")
            except Exception as e:
                print(f"Erreur lors de l'envoi du MP d'enchère : {e}")

    # --- LES BOUTONS ---
    @discord.ui.button(label="+ 1,000", style=discord.ButtonStyle.primary, custom_id="bid_1000")
    async def bid_1k(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process_bid(interaction, 1000)

    @discord.ui.button(label="+ 2,000", style=discord.ButtonStyle.primary, custom_id="bid_2000")
    async def bid_2k(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process_bid(interaction, 2000)

    @discord.ui.button(label="+ 5,000", style=discord.ButtonStyle.primary, custom_id="bid_5000")
    async def bid_5k(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process_bid(interaction, 5000)

    @discord.ui.button(label="Terminer 🛑", style=discord.ButtonStyle.success, custom_id="bid_finish", row=1)
    async def finish_auction(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("⛔ Réservé aux admins.", ephemeral=True)
            return

        auction_id = str(interaction.message.id)
        if auction_id not in bot_data["auctions"]:
            await interaction.response.send_message("❌ Enchère introuvable.", ephemeral=True)
            return

        auction = bot_data["auctions"][auction_id]
        winner_team = auction["highest_bidder"]
        price = auction["current_price"]
        player_id = auction["player_id"]

        if winner_team:
            # 1. Prélèvement
            bot_data["teams"][winner_team]["points"] -= price
            
            # 2. Transfert du joueur
            # Retrait de l'ancienne équipe
            for t_name, t_data in bot_data["teams"].items():
                member_to_remove = next((m for m in t_data["members"] if m["id"] == player_id), None) if isinstance(t_data["members"][0] if t_data["members"] else {}, dict) else (player_id if player_id in t_data["members"] else None)
                if t_name != winner_team and member_to_remove:
                    t_data["members"].remove(member_to_remove)
            
            # Ajout à la nouvelle équipe
            member_exists = any(m["id"] == player_id if isinstance(m, dict) else m == player_id for m in bot_data["teams"][winner_team]["members"])
            if not member_exists:
                bot_data["teams"][winner_team]["members"].append({
                    "id": player_id,
                    "wealth": 0
                })
            
            # 3. Annonce de victoire
            embed = discord.Embed(title="🔨 ENCHÈRE TERMINÉE (MANUEL)", color=discord.Color.gold())
            embed.description = f"Le joueur <@{player_id}> a été recruté par **{winner_team}** !"
            embed.add_field(name="Prix final", value=f"{price:,} MGP", inline=True)
            
            await interaction.channel.send(f"<@{bot_data['teams'][winner_team]['leader_id']}>", embed=embed)
            await interaction.response.send_message("✅ Enchère validée manuellement.", ephemeral=True)
        else:
            await interaction.response.send_message("✅ Enchère terminée sans aucune offre.", ephemeral=True)
            await interaction.channel.send(f"⌛ L'enchère pour <@{player_id}> a été fermée sans vainqueur.")

        # 4. Nettoyage
        del bot_data["auctions"][auction_id]
        save_data() 
        await interaction.message.edit(view=None)

    @discord.ui.button(label="Annuler 🗑️", style=discord.ButtonStyle.danger, custom_id="bid_delete", row=1)
    async def delete_auction(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("⛔ Réservé aux admins.", ephemeral=True)
            return
        
        auction_id = str(interaction.message.id)
        if auction_id in bot_data["auctions"]:
            del bot_data["auctions"][auction_id]
            save_data()
            
        await interaction.message.delete()
        await interaction.response.send_message("🗑️ Enchère annulée et supprimée.", ephemeral=True)


# --- LE COG ---
class Auctions(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.check_auctions_loop.start()
    
    async def cog_load(self):
        self.bot.add_view(AuctionView())

    def cog_unload(self):
        self.check_auctions_loop.cancel()

    @tasks.loop(seconds=10)
    async def check_auctions_loop(self):
        now = datetime.datetime.now().timestamp()
        to_remove = []

        for message_id, auction in bot_data["auctions"].items():
            if now >= auction["end_time"]:
                channel = self.bot.get_channel(auction["channel_id"])
                
                if channel:
                    winner_team = auction["highest_bidder"]
                    price = auction["current_price"]
                    player_id = auction["player_id"]

                    if winner_team:
                        # SCÉNARIO 1 : GAGNANT
                        bot_data["teams"][winner_team]["points"] -= price
                        
                        # Gestion du transfert
                        for t_name, t_data in bot_data["teams"].items():
                            member_to_remove = next((m for m in t_data["members"] if m["id"] == player_id), None) if isinstance(t_data["members"][0] if t_data["members"] else {}, dict) else (player_id if player_id in t_data["members"] else None)
                            if t_name != winner_team and member_to_remove: 
                                t_data["members"].remove(member_to_remove)

                        member_exists = any(m["id"] == player_id if isinstance(m, dict) else m == player_id for m in bot_data["teams"][winner_team]["members"])
                        if not member_exists:
                            bot_data["teams"][winner_team]["members"].append({
                                "id": player_id,
                                "wealth": 0
                            })
                        
                        # Annonce
                        embed = discord.Embed(title="🔨 ENCHÈRE TERMINÉE !", color=discord.Color.gold())
                        embed.description = f"Le joueur <@{player_id}> a été recruté par **{winner_team}** !"
                        embed.add_field(name="Prix final", value=f"{price:,} MGP", inline=True)
                        embed.add_field(name="Solde restant", value=f"{bot_data['teams'][winner_team]['points']:,} MGP", inline=True)
                        
                        await channel.send(f"<@{bot_data['teams'][winner_team]['leader_id']}>", embed=embed)
                    
                    else:
                        # SCÉNARIO 2 : PERSONNE
                        await channel.send(f"⌛ L'enchère pour <@{player_id}> est terminée sans aucune offre.")

                    try:
                        original_msg = await channel.fetch_message(int(message_id))
                        await original_msg.edit(view=None)
                    except:
                        pass

                to_remove.append(message_id)

        if to_remove:
            for mid in to_remove:
                del bot_data["auctions"][mid]
            save_data()

    @app_commands.command(name="add_auction", description="Admin: Lancer une enchère")
    @app_commands.checks.has_permissions(administrator=True)
    async def add_auction(self, interaction: discord.Interaction, joueur: discord.Member, prix: int, duree: int):
        end_time = datetime.datetime.now() + timedelta(minutes=duree)
        timestamp_fin = int(end_time.timestamp())

        embed = discord.Embed(title="🔨 ENCHÈRE OUVERTE !", color=discord.Color.purple())
        embed.description = f"Le joueur {joueur.mention} est sur le marché des transferts !"
        embed.set_thumbnail(url=joueur.display_avatar.url)
        
        embed.add_field(name="⏳ Fin de l'enchère", value=f"<t:{timestamp_fin}:R>", inline=False)
        embed.add_field(name="💰 Offre actuelle", value=f"**{prix:,} MGP**", inline=True)
        embed.add_field(name="🏆 Meneur", value="Personne", inline=True)

        await interaction.response.send_message(embed=embed, view=AuctionView())
        
        message = await interaction.original_response()
        
        bot_data["auctions"][str(message.id)] = {
            "player_id": joueur.id,
            "start_price": prix,
            "current_price": prix,
            "highest_bidder": None,
            "end_time": timestamp_fin,
            "channel_id": interaction.channel_id
        }
        save_data() 

        # --- COMMANDE : LISTER LES ENCHÈRES ---
    @app_commands.command(name="get_auctions", description="Voir la liste de toutes les enchères en cours")
    async def get_auctions(self, interaction: discord.Interaction):
        if not bot_data["auctions"]:
            await interaction.response.send_message("💤 Aucune enchère en cours pour le moment.", ephemeral=True)
            return

        embed = discord.Embed(title="🔨 Marché des Transferts", color=discord.Color.orange())
        
        count = 0
        for msg_id, info in bot_data["auctions"].items():
            player_id = info["player_id"]
            price = info["current_price"]
            end_time = info["end_time"]
            leader = info["highest_bidder"] if info["highest_bidder"] else "Personne"

            # On crée un lien cliquable vers le message de l'enchère pour y aller vite
            # Format : https://discord.com/channels/ID_SERVEUR/ID_SALON/ID_MESSAGE
            jump_url = f"https://discord.com/channels/{interaction.guild_id}/{info['channel_id']}/{msg_id}"

            embed.add_field(
                name=f"Joueur : <@{player_id}>", 
                value=f"💰 **{price:,} MGP** | 🏆 {leader}\n⏳ <t:{end_time}:R>\n🔗 [Aller à l'enchère]({jump_url})",
                inline=False
            )
            count += 1
            
            # Limite pour éviter que le message soit trop gros (Discord limite à 25 fields)
            if count >= 20:
                embed.set_footer(text="Et d'autres enchères...")
                break

        await interaction.response.send_message(embed=embed)

    # --- COMMANDE : DÉTAILS D'UNE ENCHÈRE ---
    @app_commands.command(name="auction_info", description="Voir les détails de l'enchère d'un joueur")
    @app_commands.describe(joueur="Le joueur dont vous cherchez l'enchère")
    async def auction_info(self, interaction: discord.Interaction, joueur: discord.Member):
        # On cherche si ce joueur est dans une enchère active
        found_auction = None
        found_msg_id = None

        for msg_id, info in bot_data["auctions"].items():
            if info["player_id"] == joueur.id:
                found_auction = info
                found_msg_id = msg_id
                break
        
        if not found_auction:
            await interaction.response.send_message(f"❌ Aucune enchère en cours pour {joueur.mention}.", ephemeral=True)
            return

        # Récupération des infos
        price = found_auction["current_price"]
        start_price = found_auction["start_price"]
        leader = found_auction["highest_bidder"] if found_auction["highest_bidder"] else "Aucune offre"
        end_time = found_auction["end_time"]
        
        # Lien vers le message
        jump_url = f"https://discord.com/channels/{interaction.guild_id}/{found_auction['channel_id']}/{found_msg_id}"

        embed = discord.Embed(title=f"🔎 Détails : {joueur.display_name}", color=discord.Color.gold())
        embed.set_thumbnail(url=joueur.display_avatar.url)
        
        embed.add_field(name="💰 Prix Actuel", value=f"**{price:,} MGP**", inline=True)
        embed.add_field(name="🏁 Prix de départ", value=f"{start_price:,} MGP", inline=True)
        embed.add_field(name="🏆 Meneur", value=f"**{leader}**", inline=True)
        embed.add_field(name="⏳ Fin", value=f"<t:{end_time}:R> (<t:{end_time}:F>)", inline=False)
        embed.add_field(name="🔗 Action", value=f"[👉 Cliquer ici pour enchérir]({jump_url})", inline=False)

        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Auctions(bot))