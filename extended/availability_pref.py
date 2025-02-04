from discord.ext import commands
from utils.user_preferences import load_data_pref ,save_data_pref
from discord import app_commands
async def setup(bot):
    await bot.add_cog(AvailabilityCog(bot))

class AvailabilityCog(commands.Cog):
    def __init__(self,bot):
        self.bot = bot
        self.data_file = 'data/user_availability.json'
        self.data = load_data_pref(self.data_file)

        
    @commands.hybrid_command(name="set_availability", description="Set your availability preferences" )
    @app_commands.describe(
        day_of_week  = "jour de la semaine, ex : lundi , mardi ...",
        start_time = "format HH:MM, optionnel",
        end_time= "format HH:MM , optionnel"
    )
    async def set_availability(self,ctx,day_of_week: str, start_time:str , end_time:str):
            """
        Set the user's availability preferences for a specific day of the week.
        - If no start or end time is provided, the user is available all day.
        - If only end time is provided, the user is available from the start of the day until the specified end time.
        - If only start time is provided, the user is available from the specified start time until the end of the day.
        - If both start and end times are provided, the user is available within the specified time range.
        Example:
        - /set_availability day_of_week: "Monday"
        - /set_availability day_of_week: "Monday" start_time: "13:00"
        - /set_availability day_of_week: "Monday" end_time: "15:00"
        - /set_availability day_of_week: "Monday" start_time: "13:00" end_time: "15:00"
        """
            user_id = str(ctx.author.id)

            days = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
            if day_of_week.lower() not in days:
                await ctx.send("Jour de semaine invalide. Entrer un jour de semaine valide (ex., Lundi, Mardis, etc.).")
                return
            
            if start_time and not (len(start_time) == 5 and start_time[2] == ':'):
                await ctx.send("Temps de debut invalide .Utiliser HH:MM (ex., 13:00).")
                return
            if end_time and not (len(end_time) == 5 and end_time[2] == ':'):
                await ctx.send("Temps de fin invalide. Utiliser HH:MM (ex., 15:00).")
                return
            
            if user_id not in self.data:
                self.data[user_id] = {}

            availability = {}
            if not start_time and not end_time:
                availability["all_day"] = True
            else:
                availability["all_day"] = False
                if start_time:
                    availability["start_time"] = start_time
                if end_time:
                    availability["end_time"] = end_time
                
            self.data[user_id][day_of_week.lower()] = availability
            save_data_pref(self.data_file,self.data)

            if availability["all_day"]:
                response = f"Your availability for {day_of_week.capitalize()} has been set to **all day**."
            else:
                if "start_time" in availability and "end_time" in availability:
                    response = f"Your availability for {day_of_week.capitalize()} has been set from **{start_time} to {end_time}**."
                elif "start_time" in availability:
                    response = f"Your availability for {day_of_week.capitalize()} has been set from **{start_time} to the end of the day**."
                elif "end_time" in availability:
                    response = f"Your availability for {day_of_week.capitalize()} has been set from the **start of the day to {end_time}**."

            await ctx.send(response)          

    async def setup(bot):
        await bot.add_cog(AvailabilityCog(bot))