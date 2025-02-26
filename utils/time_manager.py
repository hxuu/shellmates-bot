from datetime import datetime, timedelta
from typing import Optional
import pytz
import re

class TimeManagement:
    def __init__(self):
        self.timezones = {}

    def set_timezone(self, user_id: int, timezone: str) -> tuple[bool, str]:
        """Set user's timezone."""
        try:
            pytz.timezone(timezone)
            self.timezones[user_id] = timezone
            return True, f"Timezone set to {timezone}"
        except pytz.exceptions.UnknownTimeZoneError:
            return False, "Invalid timezone. Use format like 'America/New_York'"

    def parse_time(self, time_input: str, user_id: Optional[int] = None) -> tuple[Optional[datetime], str]:
        """Parse time into datetime object."""
        try:
            user_tz = pytz.timezone(self.timezones.get(user_id, 'UTC'))
            time_input = time_input.strip().lower()
            current_time = datetime.now(user_tz)

            if time_input.startswith('in '):
                time_parts = time_input[3:].split()
                if len(time_parts) < 2:
                    return None, "Invalid format. Use 'in X hours/minutes'"

                try:
                    amount = int(time_parts[0])
                    if amount <= 0:
                        return None, "Time amount must be positive"
                except ValueError:
                    return None, "Invalid number format for time amount"

                unit = time_parts[1].lower()
                if 'hour' in unit:
                    return current_time + timedelta(hours=amount), "Success"
                elif 'minute' in unit:
                    return current_time + timedelta(minutes=amount), "Success"
                return None, "Invalid time unit. Use 'hours' or 'minutes'"
            else:
                try:
                    specific_time = datetime.strptime(time_input, "%Y-%m-%d %H:%M")
                    if specific_time < current_time:
                        return None, "Time cannot be in the past"
                    specific_time = user_tz.localize(specific_time)
                    return specific_time.astimezone(pytz.UTC), "Success"
                except ValueError:
                    return None, "Invalid format. Use YYYY-MM-DD HH:MM"

        except pytz.UnknownTimeZoneError:
            return None, "Error: Invalid timezone specified for user."
        except Exception as e:
            return None, f"Error: {str(e)}"

    def convert_to_user_timezone(self, utc_time: datetime, user_id: int) -> tuple[datetime, str]:
        """Convert UTC time to user timezone."""
        try:
            user_tz = pytz.timezone(self.timezones.get(user_id, 'UTC'))
            return utc_time.astimezone(user_tz), "Success"
        except pytz.UnknownTimeZoneError:
            return utc_time, "Conversion failed: Invalid timezone for user."
        except Exception as e:
            return utc_time, f"Conversion failed: {str(e)}"
    def parse_relative_time(time_str):
        """Parse relative time strings like '30 minutes', '2 hours', '1 day', etc."""
        time_str = time_str.lower()
        units = {
            'minute': 1,
            'minutes': 1,
            'min': 1,
            'mins': 1,
            'm': 1,
            'hour': 60,
            'hours': 60,
            'hr': 60,
            'hrs': 60,
            'h': 60,
            'day': 1440,
            'days': 1440,
            'd': 1440,
            'week': 10080,
            'weeks': 10080,
            'w': 10080
        }
    
        pattern = r'(\d+)\s*([a-zA-Z]+)'
        match = re.match(pattern, time_str)
    
        if not match:
            raise ValueError("Format de temps invalide")
        
        amount = int(match.group(1))
        unit = match.group(2)
    
        if unit not in units:
            raise ValueError("Unité de temps non reconnue")
        
        return timedelta(minutes=amount * units[unit])

