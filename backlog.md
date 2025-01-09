============================================
## Tasks Done So Far

- Setting up the Discord bot structure.
- Writing a "Hello, world!" bot with basic commands (`!hello`, `!ping`, `!say`).
- Implemented the `!schedule` command to schedule meetings/tasks.
- Implemented the `!reminders` command to list all upcoming reminders for the user.
- Implemented the `!delete <ID>` command to cancel a specific reminder.
- Added a `!help` command to display all available commands and usage examples.

============================================
## Tasks Yet To Be Done... (just type your name inside [] to indicate you're working on it)

> Note that all work should be under core/ directory which should be organized per command.


### Reminder Mechanism
- [ Nabil ] Create a background task or scheduler to check for upcoming reminders.
- [ ayoub ] Send reminders 10 minutes before events by default.
- [ ayoub ] Support customizable lead times (e.g., 30 minutes).
- [ Nabil ] Enable reminders via Direct Messages (DMs) or in specific channels.


### Time Management
- [ selma] Add support for both absolute (`2024-12-30 15:00`) and relative times (`in 2 hours`).
- [ selma] Implement timezone support:
  -[selma] Allow users to set their preferred timezone.
  -[selma] Handle automatic timezone conversions.


### Data Handling
- [ nihad] Store reminders persistently in `data/reminders.json`.
- [nihad ] Add error handling for invalid inputs or missing fields in commands.


### Testing and Documentation
- [ ] Test all implemented commands thoroughly.
- [ ] Add documentation for:
  - Setting up and running the bot.
  - Using each command with examples.
  - Troubleshooting common issues.

============================================


