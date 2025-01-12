#J'ai ajouté ce code pour tester si le bot est bien connecté ou non et pour exécuter trois commandes :

#!hello : Le bot affiche le message "Hello, world !"
#!say "ton message ici" : Le bot affiche ton message
#!ping : Le bot affiche "Pong"
#remarque: n'oubilez pas d'enter votre bot token
import discord
import os
import json
from discord.ext import commands
from utils import jeson
from dotenv import load_dotenv

# Load bot config using JSON
bot_config = jeson.parse_json('./data/config.json')

# Load environment variables
load_dotenv()

# Create an instance of the bot
intents = discord.Intents.default()
intents.message_content = True  # Ensure the bot can read message content
bot = commands.Bot(command_prefix=bot_config['COMMAND_PREFIX'], intents=intents)

# Path to reminders.json
REMINDERS_FILE = "./data/reminders.json"

# Ensure the data directory exists
os.makedirs(os.path.dirname(REMINDERS_FILE), exist_ok=True)

# Load reminders from the file
def load_reminders():
    if os.path.exists(REMINDERS_FILE):
        try:
            with open(REMINDERS_FILE, "r") as file:
                return json.load(file)
        except json.JSONDecodeError:
            print("Error: reminders.json is corrupted. Starting with an empty list.")
    return []

# Save reminders to the file
def save_reminders(reminders):
    try:
        with open(REMINDERS_FILE, "w") as file:
            json.dump(reminders, file, indent=4)
    except Exception as e:
        print(f"Error saving reminders: {e}")

# Initialize reminders
reminders = load_reminders()

# Event when the bot is ready
@bot.event
async def on_ready():
    print('=============================================')
    print(f'Bot connected as {bot.user}')
    print('=============================================')

# Simple command examples
@bot.command()
async def hello(ctx):
    await ctx.send('Hello, world!')

@bot.command()
async def ping(ctx):
    await ctx.send('Pong!')

@bot.command()
async def say(ctx, *, message):
    await ctx.send(message)

# Add a reminder command
@bot.command()
async def add_reminder(ctx, *, message: str = None):
    try:
        if not message:
            await ctx.send("Error: You must specify a reminder message.")
            return

        # Add the reminder to the list
        reminders.append({"user": ctx.author.name, "message": message})
        save_reminders(reminders)
        await ctx.send(f"Reminder added: '{message}'")
    except Exception as e:
        await ctx.send(f"An error occurred: {e}")

# List reminders command
@bot.command()
async def list_reminders(ctx):
    if not reminders:
        await ctx.send("No reminders found.")
        return

    reminder_list = "\n".join([f"{i + 1}. {r['user']}: {r['message']}" for i, r in enumerate(reminders)])
    await ctx.send(f"Here are the reminders:\n{reminder_list}")

# Delete a reminder command
@bot.command()
async def delete_reminder(ctx, index: int = None):
    try:
        if index is None or index <= 0 or index > len(reminders):
            await ctx.send("Error: Invalid reminder number. Use the `list_reminders` command to view valid numbers.")
            return

        removed = reminders.pop(index - 1)
        save_reminders(reminders)
        await ctx.send(f"Deleted reminder: '{removed['message']}'")
    except Exception as e:
        await ctx.send(f"An error occurred: {e}")

# Run the bot with your token
bot.run('')
