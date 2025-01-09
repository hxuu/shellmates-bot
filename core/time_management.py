import uuid
from utils.reminders import load_reminders, save_reminders


def setup(bot):
    @bot.hybrid_command()
    async def schedule(ctx, title: str, date: str, time: str):
        """
        Schedule a new reminder.

        Parameters:
        - title (str): The title or description of the reminder.
        - date (str): The date for the reminder in the format YYYY-MM-DD.
        - time (str): The time for the reminder in the format HH:MM.

        Usage:
        !schedule <title> <date> <time>

        Example:
        !schedule "Team meeting" 2024-12-30 15:00

        This will schedule a reminder titled "Team meeting" for December 30, 2024, at 3:00 PM.
        """
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

    @bot.hybrid_command()
    async def reminders(ctx):
        """
        List all reminders for the user.

        Usage:
        !reminders

        This command will display all reminders scheduled by the user.
        Each reminder includes:
        - Title
        - Date
        - Time
        - Reminder ID (for deletion)
        """
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

    @bot.hybrid_command()
    async def delete(ctx, reminder_id: str):
        """
        Delete a specific reminder by its ID.

        Parameters:
        - reminder_id (str): The unique ID of the reminder to delete.

        Usage:
        !delete <reminder_id>

        Example:
        !delete a1b2c3d4

        This will delete the reminder with the specified ID if it exists and belongs to the user.
        """
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
