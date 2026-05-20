import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button, Select
import asyncio
from datetime import datetime, timedelta
from utils.data_manager import bot_data, save_data

class EventView(View):
    def __init__(self, event_id, creator_id):
        super().__init__(timeout=None)
        self.event_id = event_id
        self.creator_id = creator_id

    @discord.ui.button(label="Participer", style=discord.ButtonStyle.green, custom_id="participate")
    async def participate(self, interaction: discord.Interaction, button: Button):
        await self.handle_participate(interaction)

    @discord.ui.button(label="Se désinscrire", style=discord.ButtonStyle.red, custom_id="unregister")
    async def unregister(self, interaction: discord.Interaction, button: Button):
        await self.handle_unregister(interaction)

    @discord.ui.button(label="Terminer l'event", style=discord.ButtonStyle.grey, custom_id="finish_event")
    async def finish_event(self, interaction: discord.Interaction, button: Button):
        # Only allow the creator to finish the event
        if interaction.user.id != self.creator_id:
            await interaction.response.send_message("❌ Seul l'organisateur peut terminer l'event.", ephemeral=True)
            return
        await self.handle_finish_event(interaction)

    async def handle_participate(self, interaction: discord.Interaction):
        event_data = bot_data["events"].get(self.event_id)
        if not event_data:
            await interaction.response.send_message("❌ Cet événement n'existe plus.", ephemeral=True)
            return

        user_id = str(interaction.user.id)
        if user_id in event_data["participants"]:
            await interaction.response.send_message("✅ Tu es déjà inscrit à cet événement.", ephemeral=True)
            return

        # Add participant
        event_data["participants"].append(user_id)
        save_data()

        # Update the embed
        embed = interaction.message.embeds[0]
        participant_count = len(event_data["participants"])
        # Find the field with participants and update it
        for i, field in enumerate(embed.fields):
            if field.name == "Participants":
                embed.set_field_at(i, name="Participants", value=f"{participant_count} participants", inline=True)
                break

        await interaction.response.edit_message(embed=embed, view=self)
        await interaction.followup.send(f"✅ Tu t'es inscrit à l'événement !", ephemeral=True)

    async def handle_unregister(self, interaction: discord.Interaction):
        event_data = bot_data["events"].get(self.event_id)
        if not event_data:
            await interaction.response.send_message("❌ Cet événement n'existe plus.", ephemeral=True)
            return

        user_id = str(interaction.user.id)
        if user_id not in event_data["participants"]:
            await interaction.response.send_message("❌ Tu n'es pas inscrit à cet événement.", ephemeral=True)
            return

        # Remove participant
        event_data["participants"].remove(user_id)
        save_data()

        # Update the embed
        embed = interaction.message.embeds[0]
        participant_count = len(event_data["participants"])
        # Find the field with participants and update it
        for i, field in enumerate(embed.fields):
            if field.name == "Participants":
                embed.set_field_at(i, name="Participants", value=f"{participant_count} participants", inline=True)
                break

        await interaction.response.edit_message(embed=embed, view=self)
        await interaction.followup.send(f"✅ Tu t'es désinscrit de l'événement.", ephemeral=True)

    async def handle_finish_event(self, interaction: discord.Interaction):
        event_data = bot_data["events"].get(self.event_id)
        if not event_data:
            await interaction.response.send_message("❌ Cet événement n'existe plus.", ephemeral=True)
            return

        if not event_data["participants"]:
            await interaction.response.send_message("❌ Aucun participant inscrit à l'événement.", ephemeral=True)
            return

        # Disable all buttons
        for item in self.children:
            item.disabled = True

        await interaction.response.edit_message(view=self)

        # Create a select menu to choose winner
        options = []
        for participant_id in event_data["participants"]:
            try:
                user = await interaction.client.fetch_user(int(participant_id))
                options.append(discord.SelectOption(label=user.name, value=participant_id))
            except:
                options.append(discord.SelectOption(label=f"User {participant_id}", value=participant_id))

        select = Select(
            placeholder="Choisir le vainqueur...",
            options=options[:25],  # Discord limit
            custom_id=f"winner_select_{self.event_id}"
        )

        async def select_callback(select_interaction):
            if select_interaction.user.id != self.creator_id:
                await select_interaction.response.send_message("❌ Seul l'organisateur peut choisir le vainqueur.", ephemeral=True)
                return

            winner_id = select_interaction.data["values"][0]
            await self.award_winner(interaction, winner_id, select_interaction)

        select.callback = select_callback

        view = View()
        view.add_item(select)

        await interaction.followup.send(
            "🏆 Choisis le vainqueur de l'événement :",
            view=view,
            ephemeral=True
        )

    async def award_winner(self, original_interaction, winner_id, select_interaction):
        event_data = bot_data["events"].get(self.event_id)
        if not event_data:
            await select_interaction.response.send_message("❌ Cet événement n'existe plus.", ephemeral=True)
            return

        amount = event_data["amount"]

        # Get winner info
        try:
            winner_user = await select_interaction.client.fetch_user(int(winner_id))
            winner_name = winner_user.name
        except:
            winner_name = f"User {winner_id}"

        # Find the winner in any team and add wealth to both member and team
        winner_found = False
        for _, team_data in bot_data["teams"].items():
            # Find member
            member_obj = None
            for i, m_entry in enumerate(team_data["members"]):
                if isinstance(m_entry, dict):
                    if m_entry.get("id") == int(winner_id):
                        member_obj = m_entry
                        break
                elif isinstance(m_entry, (int, float)):
                    if int(m_entry) == int(winner_id):
                        member_obj = {"id": int(m_entry), "wealth": 0}
                        team_data["members"][i] = member_obj
                        break

            if member_obj:
                # Add wealth to member and team
                member_obj["wealth"] += amount
                team_data["points"] += amount
                winner_found = True
                break

        if winner_found:
            save_data()

            # Notify in the original channel
            embed = discord.Embed(
                title="🎉 Événement terminé !",
                description=f"Le vainqueur est **{winner_name}** ! Il/Elle remporte **{amount:,} MGP**.",
                color=discord.Color.gold()
            )
            await original_interaction.channel.send(embed=embed)

            # Confirm to admin
            await select_interaction.response.send_message(
                f"✅ {winner_name} a reçu {amount:,} MGP !",
                ephemeral=True
            )
        else:
            await select_interaction.response.send_message(
                "❌ Erreur : le vainqueur n'est pas trouvé dans aucune équipe.",
                ephemeral=True
            )
            return

        # Remove event
        del bot_data["events"][self.event_id]
        save_data()

class Events(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="create_event", description="Admin: Créer un nouvel événement")
    @app_commands.checks.has_permissions(administrator=True)
    async def create_event(
        self,
        interaction: discord.Interaction,
        amount: int,
        duration_minutes: int,
        description: str = "Aucune description fournie"
    ):
        """Crée un nouvel événement avec participation via boutons"""

        if amount <= 0:
            await interaction.response.send_message("❌ Le montant doit être supérieur à 0.", ephemeral=True)
            return

        if duration_minutes <= 0:
            await interaction.response.send_message("❌ La durée doit être supérieure à 0 minutes.", ephemeral=True)
            return

        # Generate unique event ID
        event_id = f"event_{datetime.now().timestamp()}"

        # Store event data
        bot_data["events"][event_id] = {
            "amount": amount,
            "duration_minutes": duration_minutes,
            "description": description,
            "creator_id": interaction.user.id,
            "created_at": datetime.now().isoformat(),
            "participants": [],
            "active": True
        }
        save_data()

        # Create embed
        embed = discord.Embed(
            title="🎉 Nouvel Événement !",
            description=description,
            color=discord.Color.blue()
        )
        embed.add_field(name="Récompense", value=f"{amount:,} MGP", inline=True)
        embed.add_field(name="Participants", value="0 participants", inline=True)
        embed.add_field(name="Durée", value=f"{duration_minutes} minutes", inline=True)
        embed.add_field(name="Organisateur", value=interaction.user.mention, inline=True)
        embed.timestamp = datetime.now()

        # Create view with buttons
        view = EventView(event_id, interaction.user.id)

        await interaction.response.send_message(embed=embed, view=view)

        # Schedule auto-end if needed (optional)
        # You could add a background task to auto-end events after duration

    @app_commands.command(name="list_events", description="Lister les événements actifs")
    async def list_events(self, interaction: discord.Interaction):
        """Liste tous les événements actifs"""
        active_events = [
            (eid, event) for eid, event in bot_data["events"].items()
            if event.get("active", False)
        ]

        if not active_events:
            await interaction.response.send_message("❌ Aucun événement actif.", ephemeral=True)
            return

        embed = discord.Embed(
            title="📋 Événements Actifs",
            color=discord.Color.blue()
        )

        for event_id, event in active_events[:10]:  # Limit to 10
            creator = await self.bot.fetch_user(event["creator_id"])
            creator_name = creator.name if creator else "Inconnu"

            embed.add_field(
                name=f"🎪 {event['team'] if 'team' in event else 'N/A'} - {event['amount']:,} MGP",
                value=f"Organisateur: {creator_name}\nParticipants: {len(event['participants'])}\nDurée: {event['duration_minutes']} min\nID: {event_id[-8:]}",
                inline=True
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="cancel_event", description="Annuler un événement actif (Admin seulement)")
    @app_commands.checks.has_permissions(administrator=True)
    async def cancel_event(self, interaction: discord.Interaction, event_id: str):
        """Annule un événement par son ID"""
        # Rechercher l'event par ID complet ou par les 8 derniers caractères
        target_event_id = None
        for eid in bot_data["events"].keys():
            if eid == event_id or eid.endswith(event_id):
                target_event_id = eid
                break

        if not target_event_id:
            await interaction.response.send_message(
                f"❌ Aucun événement actif trouvé avec l'ID: `{event_id}`\n"
                f"Utilisez `/list_events` pour voir les événements actifs et leurs IDs complets.",
                ephemeral=True
            )
            return

        event_data = bot_data["events"].get(target_event_id)
        if not event_data or not event_data.get("active", False):
            await interaction.response.send_message(
                f"❌ L'événement avec l'ID `{target_event_id[-8:]}` n'est plus actif.",
                ephemeral=True
            )
            return

        # Marquer l'event comme inactif plutôt que de le supprimer totalement
        # (garder l'historique éventuel)
        event_data["active"] = False
        save_data()

        await interaction.response.send_message(
            f"✅ L'événement `{target_event_id[-8:]}` a été annulé avec succès.",
            ephemeral=True
        )

async def setup(bot):
    await bot.add_cog(Events(bot))