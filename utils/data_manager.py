import json
import os
import discord
from discord import app_commands

DATA_FILE = "data.json"

# --- GESTION DES DONNÉES ---
def load_data():
    if not os.path.exists(DATA_FILE):
        return {"teams": {}, "auctions": {}, "events": {}}
    try:
        with open(DATA_FILE, "r") as f:
            data = json.load(f)
            if "teams" not in data: data["teams"] = {}
            if "auctions" not in data: data["auctions"] = {}
            if "events" not in data: data["events"] = {}
            return data
    except:
        return {"teams": {}, "auctions": {}, "events": {}}

bot_data = load_data()

def save_data():
    with open(DATA_FILE, "w") as f:
        json.dump(bot_data, f, indent=4)

# --- AUTOCOMPLÉTION PARTAGÉE ---
async def team_autocomplete(interaction: discord.Interaction, current: str):
    team_names = list(bot_data["teams"].keys())
    filtered_teams = [
        team for team in team_names 
        if current.lower() in team.lower()
    ]
    return [
        app_commands.Choice(name=team, value=team)
        for team in filtered_teams
    ][:25]