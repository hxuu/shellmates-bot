import uuid
import pytz
import json
from datetime import datetime, timedelta
from dateutil.parser import parse

#functions to load and save reminders
def load_reminders():
    try:
        with open("reminders.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"users": {}}

def save_reminders(data):
    with open("reminders.json", "w") as f:
        json.dump(data, f, indent=4) 
def validate_relative_time(time_str):
    """
    validate the relative time formats

    Parameters:
    - time_str (str): Relative time string (examle "in 3 hours").

    Returns:
    - (bool, int, str): line with validity (booléen), quantity (int), and unit (str).
    """
    try:
        if time_str.startswith("in"):
            amount, unit = time_str[3:].strip().split(" ", 1)
            amount = int(amount)  # ensure amount is an int
            if unit not in ["hour", "hours", "minute", "minutes", "day", "days"]:
                return False, 0, ""  # invalid unit
            return True, amount, unit
        return False, 0, ""  # invalid relative time format
    except ValueError:
        return False, 0, ""  # error parsing amount or unit



def setup(bot):
    @bot.hybrid_command()
    async def set_timezone(ctx, timezone: str):
        """
        settin the user timezone.

        Parameters:
        - timezone (str): The user's timezone ( "europe/paris").
        """
        try:
            if timezone not in pytz.all_timezones:
                await ctx.send("❌ Invalid timezone. Please provide a valid timezone (e.g., 'Europe/Paris').")
                return

            reminders_data = load_reminders()
            user_data = reminders_data["users"].get(ctx.author.name, {"timezone": "UTC", "reminders": []})
            user_data["timezone"] = timezone  # update user timezone
            reminders_data["users"][ctx.author.name] = user_data

            save_reminders(reminders_data)

            await ctx.send(f"✅ Timezone set to {timezone}.")
        except Exception as e:
            await ctx.send("❌ An error occurred while setting the timezone.")
            print(f"Error: {e}")

    @bot.hybrid_command()
    async def schedule(ctx, title: str, time_str: str):
        """
        Schedule a new reminder with an absolute or relative time.

        Parameters:
        - title (str): Reminder title/description.
        - time_str (str): Time as absolute (e.g., "2024-12-30 15:00") or relative (e.g., "in 2 hours").
        """
        try:
            reminders_data = load_reminders()
            user_data = reminders_data["users"].get(ctx.author.name, {"timezone": "UTC", "reminders": []})

            # getting user timezone
            user_timezone = user_data["timezone"]
            tz = pytz.timezone(user_timezone)

            # parsing time absolute and relative
            if time_str.startswith("in"):
                valid, amount, unit = validate_relative_time(time_str)
                if not valid:
                    await ctx.send("❌ Invalid relative time format. Use 'in X hours' or 'in X minutes'.")
                    return

                now = datetime.now(tz)
                if unit in ["hour", "hours"]:
                    reminder_time = now + timedelta(hours=amount)
                elif unit in ["minute", "minutes"]:
                    reminder_time = now + timedelta(minutes=amount)
                elif unit in ["day", "days"]:
                    reminder_time = now + timedelta(days=amount)
            else:
                reminder_time = parse(time_str)
                reminder_time = tz.localize(reminder_time)

            # add reminder to user's data
            reminder_id = str(uuid.uuid4())
            reminder = {
                "id": reminder_id,
                "title": title,
                "time": reminder_time.isoformat()  # Save time in ISO 8601 format
            }
            user_data["reminders"].append(reminder)
            reminders_data["users"][ctx.author.name] = user_data

            save_reminders(reminders_data)

            formatted_time = reminder_time.strftime("%Y-%m-%d %H:%M %Z")
            await ctx.send(f"✅ Reminder scheduled: {title} at {formatted_time}. (ID: {reminder_id})")
        except Exception as e:
            await ctx.send("❌ An error occurred while scheduling the reminder.")
            print(f"Error: {e}")

    @bot.hybrid_command()
    async def reminders(ctx):
        """
        List all reminders for the user.
        """
        try:
            reminders_data = load_reminders()
            user_data = reminders_data["users"].get(ctx.author.name, {"timezone": "UTC", "reminders": []})

            user_timezone = user_data["timezone"]
            tz = pytz.timezone(user_timezone)
            user_reminders = user_data["reminders"]

            if user_reminders:
                response = "**Your reminders:**\n"
                for i, reminder in enumerate(user_reminders, start=1):
                    reminder_time = datetime.fromisoformat(reminder["time"]).astimezone(tz)
                    formatted_time = reminder_time.strftime("%Y-%m-%d %H:%M %Z")
                    response += f"{i}. **{reminder['title']}** - {formatted_time} (ID: {reminder['id']})\n"
            else:
                response = "You have no reminders."

            await ctx.send(response)
        except Exception as e:
            await ctx.send("❌ An error occurred while listing reminders.")
            print(f"Error: {e}")

    @bot.hybrid_command()
    async def delete(ctx, reminder_id: str):
        """
        Delete a specific reminder by its ID.

        Parameters:
        - reminder_id (str): The unique ID of the reminder to delete.
        """
        try:
            reminders_data = load_reminders()
            user_data = reminders_data["users"].get(ctx.author.name, {"timezone": "UTC", "reminders": []})

            reminder_to_delete = next((r for r in user_data["reminders"] if r["id"] == reminder_id), None)

            if reminder_to_delete:
                user_data["reminders"].remove(reminder_to_delete)
                reminders_data["users"][ctx.author.name] = user_data
                save_reminders(reminders_data)
                await ctx.send(f"✅ Reminder deleted: {reminder_to_delete['title']} (ID: {reminder_id})")
            else:
                await ctx.send("❌ Invalid reminder ID.")
        except Exception as e:
            await ctx.send("❌ An error occurred while deleting the reminder.")
            print(f"Error: {e}")

                   
           
         
