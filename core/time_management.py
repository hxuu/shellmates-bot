import uuid
import asyncio
from datetime import datetime, timedelta
import discord
from discord.ext import commands
from utils.reminders import load_reminders, save_reminders

def setup(bot):
    # Track sent notifications to prevent duplicates
    sent_notifications = set()

    @bot.event
    async def on_ready():
        print("Starting reminder checker background task...")
        bot.loop.create_task(check_reminders(bot))

    async def check_reminders(bot):
        """
        Background task that periodically checks for upcoming reminders and sends notifications.
        """
        while True:
            try:
                current_time = datetime.now()
                reminders = load_reminders()
                reminders_to_remove = []
                
                for reminder in reminders:
                    try:
                        # Parse reminder datetime in local time
                        reminder_datetime = datetime.strptime(
                            f"{reminder['date']} {reminder['time']}", 
                            "%Y-%m-%d %H:%M"
                        )
                        
                        time_until_reminder = reminder_datetime - current_time
                        minutes_until = time_until_reminder.total_seconds() / 60
                        
                        notification_key = f"{reminder['id']}_5min"
                        print("time_until_reminder: " +  time_until_reminder)
                        # Check if reminder is due within the next 5 minutes
                        if 4 <= minutes_until <= 5 and notification_key not in sent_notifications:
                            print("4 <= minutes_until <= 5")
                            try:
                                # Get the channel where the reminder was created
                                channel = bot.get_channel(reminder["channel_id"])
                                if channel:
                                    # Create the notification message
                                    notification = f"⏰ Rappel dans 5 minutes :\n\n"
                                    
                                    # Add mentions based on specified users or default to everyone
                                    if reminder.get('mentions'):
                                        mentions = [f"<@{user_id}>" for user_id in reminder['mentions']]
                                        notification += f"{', '.join(mentions)}\n\n"
                                    else:
                                        notification += "@everyone\n\n"
                                    
                                    notification += f"**{reminder['title']}** à {reminder['time']}\n\n"
                                    notification += f"(ID: {reminder['id']})"
                                    
                                    await channel.send(notification)
                                    print(f"Sent notification for reminder {reminder['id']} in channel {channel.name}")
                                    sent_notifications.add(notification_key)
                                else:
                                    print(f"Could not find channel {reminder['channel_id']}")
                            except Exception as e:
                                print(f"Error sending reminder notification: {e}")
                                continue
                        
                        # Clean up past reminders
                        if time_until_reminder < timedelta(minutes=-5):
                            reminders_to_remove.append(reminder)
                            if notification_key in sent_notifications:
                                sent_notifications.remove(notification_key)
                    
                    except Exception as e:
                        print(f"Error processing reminder {reminder.get('id', 'unknown')}: {e}")
                        continue
                
                # Remove completed reminders
                for reminder in reminders_to_remove:
                    reminders.remove(reminder)
                if reminders_to_remove:
                    save_reminders(reminders)
                
            except Exception as e:
                print(f"Error in reminder checker: {e}")
            
            await asyncio.sleep(30)  # Check every 30 seconds instead of 60

    def format_time_until(time_delta):
    
        total_seconds = int(time_delta.total_seconds())
    
        # Calculate hours, minutes, and seconds
        days = total_seconds // 86400
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
    
        # Build the time string
        parts = []
        if days > 0:
            parts.append(f"{days} jour{'s' if days > 1 else ''}")
        if hours > 0:
            parts.append(f"{hours} heure{'s' if hours > 1 else ''}")
        if minutes > 0:
            parts.append(f"{minutes} minute{'s' if minutes > 1 else ''}")
        if seconds > 0:
            parts.append(f"{seconds} seconde{'s' if seconds > 1 else ''}")
        
        if not parts:
            return "moins d'une seconde"
        
        if len(parts) == 1:
            return parts[0]
        elif len(parts) == 2:
            return f"{parts[0]} et {parts[1]}"
        else:
            return f"{parts[0]}, {parts[1]} et {parts[2]}"
    

    @bot.hybrid_command(
        name="schedule",
        description="Programme un rappel pour une date et heure spécifiques avec mentions optionnelles",
        brief="Programme un nouveau rappel"
    )
    @discord.app_commands.describe(
        title="Le titre ou la description du rappel",
        date="La date du rappel (format: YYYY-MM-DD)",
        time="L'heure du rappel (format: HH:MM)",
        mentions="Les utilisateurs à mentionner (optionnel, mentionnez-les avec @). Si vide, mentionnera @everyone"
    )
    @commands.has_permissions(send_messages=True)
    async def schedule(ctx, title: str, date: str, time: str, *, mentions: str = None):
        """
        Schedule a new reminder.

        Parameters:
        - title (str): The title or description of the reminder.
        - date (str): The date for the reminder in the format YYYY-MM-DD.
        - time (str): The time for the reminder in the format HH:MM.
        - mentions (str, optional): Space-separated list of user mentions. If not provided, everyone will be notified.

        Usage:
        !schedule <title> <date> <time> [@user1 @user2 ...]

        Example:
        !schedule "Team meeting" 2024-12-30 15:00 @user1 @user2
        """
        try:
            # Check bot permissions in the channel
            if not ctx.channel.permissions_for(ctx.guild.me).send_messages:
                await ctx.send("❌ Je n'ai pas la permission d'envoyer des messages dans ce canal.")
                return

            # Validate date and time format
            try:
                reminder_datetime = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
                if reminder_datetime < datetime.now():
                    await ctx.send("❌ La date et l'heure doivent être dans le futur.")
                    return
            except ValueError:
                await ctx.send("❌ Format de date ou d'heure invalide. Utilisez YYYY-MM-DD HH:MM")
                return

            # Process mentions if provided
            mentioned_users = []
            if mentions:
                # Extract user IDs from mentions
                for mention in ctx.message.mentions:
                    mentioned_users.append(mention.id)

            reminder_id = str(uuid.uuid4())
            reminder = {
                "id": reminder_id,
                "user_id": ctx.author.id,
                "username": ctx.author.name,
                "channel_id": ctx.channel.id,
                "title": title,
                "date": date,
                "time": time,
                "mentions": mentioned_users if mentioned_users else None
            }
            
            reminders = load_reminders()
            reminders.append(reminder)
            save_reminders(reminders)
            
            # Calculate and show time until reminder
            time_until = reminder_datetime - datetime.now()
            formatted_time = format_time_until(time_until)

            
            response = (
                f"✅ Rappel planifié : {title}\n\n"
                f"📅 Date : {date} à {time}\n\n"
                f"⏰ Dans environ {formatted_time} \n\n"
            )
            
            if mentioned_users:
                mentioned_names = [f"<@{user_id}>" for user_id in mentioned_users]
                response += f"👥 Personnes mentionnées : {', '.join(mentioned_names)}\n\n"
            else:
                response += "👥 Notification : @everyone\n\n"
            
            response += (
                f"🆔 ID: {reminder_id}\n\n"
                f"📢 Les notifications seront envoyées dans ce canal"
            )
            
            await ctx.send(response)
            
        except Exception as e:
            await ctx.send("❌ Une erreur est survenue lors de la planification.")
            print(f"Erreur : {e}")

    @bot.hybrid_command()
    async def reminders(ctx):
        """
        List all reminders for the user.
        """
        try:
            reminders = load_reminders()
            user_reminders = [r for r in reminders if r["user_id"] == ctx.author.id]
            
            if user_reminders:
                # Sort reminders by date and time
                user_reminders.sort(key=lambda x: f"{x['date']} {x['time']}")
                
                response = "**Vos rappels :**\n\n"
                for i, reminder in enumerate(user_reminders, start=1):
                    # Get channel name
                    channel = ctx.guild.get_channel(reminder['channel_id'])
                    channel_name = channel.name if channel else "canal inconnu"
                    
                    # Calculate time until reminder
                    reminder_datetime = datetime.strptime(f"{reminder['date']} {reminder['time']}", "%Y-%m-%d %H:%M")
                    time_until = reminder_datetime - datetime.now()
                    
                    response += f"{i}. **{reminder['title']}**\n\n"
                    response += f"📅 {reminder['date']} à {reminder['time']}\n\n"
                    response += f"⏰ Dans {format_time_until(time_until)}\n\n"
                    response += f"📢 #{channel_name}\n\n"
                    
                    if reminder.get('mentions'):
                        mentions = [f"<@{user_id}>" for user_id in reminder['mentions']]
                        response += f"👥 Personnes mentionnées : {', '.join(mentions)}\n\n"
                    else:
                        response += "👥 Notification : @everyone\n\n"
                    
                    response += f"🆔 ID: {reminder['id']}\n\n"
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
        """
        try:
            reminders = load_reminders()
            user_reminders = [r for r in reminders if r["user_id"] == ctx.author.id]
            reminder_to_delete = next((r for r in user_reminders if r["id"] == reminder_id), None)

            if reminder_to_delete:
                reminders.remove(reminder_to_delete)
                save_reminders(reminders)
                await ctx.send(f"✅ Rappel supprimé : {reminder_to_delete['title']}\n\n🆔 ID: {reminder_id}")
            else:
                await ctx.send("❌ ID de rappel invalide ou ce rappel ne vous appartient pas.")
        except Exception as e:
            await ctx.send("❌ Une erreur est survenue lors de la suppression.")
            print(f"Erreur : {e}")

    @bot.hybrid_command()
    @commands.has_permissions(send_messages=True)
    async def check_permissions(ctx):
        """
        Check bot permissions in the current channel.
        """
        try:
            permissions = ctx.channel.permissions_for(ctx.guild.me)
            
            perms_list = [
                ("Send Messages", permissions.send_messages),
                ("Embed Links", permissions.embed_links),
                ("Attach Files", permissions.attach_files),
                ("Mention Everyone", permissions.mention_everyone),
                ("Manage Messages", permissions.manage_messages),
            ]
            
            response = "**Bot Permissions in this channel:**\n\n"
            for perm, value in perms_list:
                emoji = "✅" if value else "❌"
                response += f"{emoji} {perm}\n"
            
            await ctx.send(response)
        except Exception as e:
            await ctx.send("❌ Une erreur est survenue lors de la vérification des permissions.")
            print(f"Erreur : {e}")