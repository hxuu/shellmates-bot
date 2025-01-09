import uuid
from utils.reminders import load_reminders, save_reminders


def setup(bot):
    @bot.command()
    async def schedule(ctx, title: str, date: str, time: str):
        try:
            reminder_id = str(uuid.uuid4())
            reminder = {
                "id": reminder_id,
                "user": ctx.author.name,
                "title": title,
                "date": date,
                "time": time
            }
            reminders = load_reminders()
            reminders.append(reminder)
            save_reminders(reminders)
            await ctx.send(f"✅ Rappel planifié : {title} le {date} à {time}. (ID: {reminder_id})")
        except Exception as e:
            await ctx.send("❌ Une erreur est survenue lors de la planification.")
            print(f"Erreur : {e}")

    @bot.command()
    async def reminders(ctx):
        try:
            reminders = load_reminders()
            user_reminders = [r for r in reminders if r["user"] == ctx.author.name]
            if user_reminders:
                response = "**Vos rappels :**\n"
                for i, reminder in enumerate(user_reminders, start=1):
                    response += f"{i}. **{reminder['title']}** - {reminder['date']} {reminder['time']} (ID: {reminder['id']})\n"
            else:
                response = "Vous n'avez aucun rappel."
            await ctx.send(response)
        except Exception as e:
            await ctx.send("❌ Une erreur est survenue.")
            print(f"Erreur : {e}")

    @bot.command()
    async def delete(ctx, reminder_id: str):
        try:
            reminders = load_reminders()
            user_reminders = [r for r in reminders if r["user"] == ctx.author.name]
            reminder_to_delete = next((r for r in user_reminders if r["id"] == reminder_id), None)

            if reminder_to_delete:
                reminders.remove(reminder_to_delete)
                save_reminders(reminders)
                await ctx.send(f"✅ Rappel supprimé : {reminder_to_delete['title']} (ID: {reminder_id})")
            else:
                await ctx.send("❌ ID de rappel invalide.")
        except Exception as e:
            await ctx.send("❌ Une erreur est survenue lors de la suppression.")
            print(f"Erreur : {e}")
