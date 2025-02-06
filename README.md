# Shellmates Discord Bot

Welcome to the **Discord Bot** project!

---

## **Table of Contents**

1. [Project Features](#project-features)
2. [Prerequisites](#prerequisites)
3. [Installation](#installation)
4. [Configuration](#configuration)
5. [Running the Bot](#running-the-bot)
6. [Contributing (related to team work)](#contributing-related-to-team-work)

---

## **Project Features**
- Set reminders for specific dates and times.
- Schedule recurring tasks.
- Ai powered time suggestions
- Feedback and analysis for the bot
- Google calendar API integratoin
- Specific channels reminders
- Disocrd DMs feature
- Modular structure for easy feature extension.
- Hybrid commands for an easier use
- Good documentation for all the commands

---

## **Prerequisites**

Before setting up the project, ensure you have the following installed:

1. **Python** (Version 3.8 or higher) - [Download Python](https://www.python.org/downloads/)
2. **Git** - [Download Git](https://git-scm.com/downloads)
3. **A Discord Bot Token**:
   - Go to the [Discord Developer Portal](https://discord.com/developers/applications).
   - Create a new application and generate a bot token.

---

## **Installation**

1. Clone the repository:
   ```bash
   git clone https://github.com/hxuu/shellmates-bot.git
   cd shellmates-bot/
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate   # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

---

## **Configuration**

1. Navigate to the `data` directory and open the `config.json` file:
   ```json
   {
       "BOT_TOKEN": "your-bot-token-here",
       "COMMAND_PREFIX": "!",
       "DEFAULT_TIMEZONE": "UTC"
   }
   ```

   - Replace `your-bot-token-here` with your Discord bot token.
   - Customize the command prefix and timezone as needed.

2. (Optional) Update `reminders.json` if you want to predefine reminders:
   ```json
   []
   ```

---

## **Running the Bot**

1. Activate your virtual environment (if not already activated):
   ```bash
   source venv/bin/activate   # On Windows: venv\Scripts\activate
   ```

2. Run the bot:
   ```bash
   python bot.py
   ```

3. You should see the bot online in your Discord server if the setup is correct.

---

## **Project Structure Overview**

```plaintext
shellmates-bot/
├── bot.py                  # Main entry point for the bot.
├── core/                   # Core functionality module.
│   ├── __init__.py         # Initializes the core module.
│   ├── schedule.py         # Handles scheduling commands.
│   ├── reminders.py        # Handles reminder-related commands.
│   └── scheduler.py        # Background task scheduling.
├── extended/               # Extended features module.
│   └── __init__.py         # Gamification and reward logic.
├── utils/                  # Utility functions.
│   ├── __init__.py         # Initializes the utils package.
├── data/                   # Data storage.
│   ├── reminders.json      # JSON file for storing reminders.
│   └── config.json         # Configuration file.
└── README.md               # Documentation for the project.
```

---

## **Contributing (Related to team work)**

1. Fork the repository.
2. Create a new branch for your feature or fix:
   ```bash
   git checkout -b feature-name
   ```
3. Commit your changes:
   ```bash
   git commit -m "Add your message here"
   ```
4. Push to your fork:
   ```bash
   git push origin feature-name
   ```
5. Open a pull request to the main repository.

---

Important Note: Check `backlog.txt` to find pending tasks and work done so far.

