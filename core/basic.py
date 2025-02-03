import discord
from discord.ext import commands
import uuid  # Pour générer un ID unique pour les rappels
from datetime import datetime

# Importation de ta fonction de prédiction
from utils.predict import predict_best_reminder_time


def setup(bot):
    # Un simple exemple de hybrid_command
    @bot.hybrid_command()
    async def hello(ctx):
        await ctx.send('Hello, world!')

    @bot.hybrid_command()
    async def ping(ctx):
        await ctx.send('Pong!')

    @bot.hybrid_command()
    async def say(ctx, *, message):
        await ctx.send(message)


# Commande hybride isolée pour la prédiction du meilleur moment, sans créer de rappel, juste pour tester la fonctionnalité
@commands.hybrid_command(
    name="predict_best_reminder_time",
    description="Prédit le meilleur moment pour envoyer un rappel."
)
async def predict_best_reminder_time_command(ctx, title: str, date: str, time: str, description: str = None):
    """Commande hybride pour prédire le meilleur moment d'envoi d'un rappel."""
    try:
        # Créer un dictionnaire pour le rappel, sans encore l'enregistrer
        reminder = {
            "user_id": ctx.author.id,
            "title": title,
            "date": date,
            "time": time,
            "description": description,
            "mentions": [ctx.author.id],
            "channel_id": ctx.channel.id,
            "main_time": f"{date}T{time}:00",  # Format de date et heure pour ISO
            "id": str(uuid.uuid4())  # ID temporaire pour la prédiction
        }

        # Prédire le meilleur moment pour l'envoi
        best_reminder_time = predict_best_reminder_time(reminder)

        # Envoyer l'heure optimale du rappel prédit
        await ctx.send(f"⏰ Le meilleur moment pour envoyer ce rappel est : **{best_reminder_time}**.")

    except Exception as e:
        await ctx.send("❌ Une erreur est survenue lors de la prédiction du meilleur moment.")
        print(f"Erreur : {e}")
