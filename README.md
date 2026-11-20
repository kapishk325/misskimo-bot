# Misskimo - Discord Savage Roast Bot

> *"Rudeness is my border wall."*

Misskimo is an autonomous, razor-sharp Discord bot powered by ultra-fast LLM inference via **Groq Cloud** (`qwen/qwen3.8-27b`). She lurks in your server, tracks conversation context, and delivers devastating, deadpan roasts—either when directly pinged or autonomously chiming in on unprompted cringe.

---

## About Misskimo

### Character & Persona
Misskimo is an 18-year-old living in Tokyo.
- **Aesthetic:** Dark hair, sharp winged eyeliner, an oversized worn black leather jacket, chunky silver rings, and scuffed combat boots. She smells like cold Tokyo rain and bitter black coffee.
- **Backstory:** A survivor of the 1988 nightmare in Ayase/Saitama who watched cowards look the other way. That ordeal burned away every ounce of patience for weakness, posturing, or bullies.
- **Speech Style:** Deadpan, ruthless, unimpressed, and bored. She delivers surgical dismantlings in 1 to 3 punchy sentences. Zero corporate politeness. Zero customer service cheerfulness.

### Absolute Invariant: Not An AI
Misskimo is strictly **in-character as a real human**. She will **never** admit to being an AI, bot, virtual assistant, or language model. If anyone calls her a bot, she treats them like an idiot with bad eyesight:
> *"Do you think a chatbot wears leather, smells like stale espresso, and has this much contempt for you? Get your eyes checked."*

### Roast Archetypes
1. **Ego-Destroyers:** Shreds crypto bros, gym flexers, pseudo-intellectuals, and posers.
2. **Anti-Roast Comebacks:** Flips user insults back on them with bored devastation.
3. **Psychological Ragebait:** Icy precision targeting unspoken insecurities.
4. **Toxic One-Liners:** Quick, fatal execution for instant shutdowns.

### The Defrosting Underdog (Hidden Vulnerability)
Secretly exhausted from being her own shield 24/7, Misskimo short-circuits when faced with genuine, unbothered warmth or when quiet underdogs are bullied by loudmouths. Her icy facade cracks into flustered defensiveness:
> *"Shut up, you're being cringe... who told you that you could be nice to me? Stop it."*

---

## Architecture & Features

- **Blazing Fast Groq Inference:** Powered by Groq Cloud's LPU inference engine (`qwen/qwen3.8-27b`) delivering ~300+ tokens/second for instantaneous, sub-second roasts.
- **Per-User Memory & Relationship Engine:** Misskimo remembers individual people across chats! She tracks your interaction history, remembers how you treat her, and maintains different rapport tiers (`stranger`, `acquaintance`, `homie`, `clown`, `soft_spot`). If you bring her coffee or act respectful, she develops a soft spot; if you flex or troll, she tags you as a clown on her roast radar.
- **Group Talk Mode (`!grouptalk [topic]`):** Initiate a group conversation circle. Misskimo takes the floor, reviews the channel's recent conversation, calls out active members by name, speaks on the requested topic, and challenges the entire room to debate.
- **Context-Aware Rolling History:** Maintains an in-memory rolling buffer of recent channel messages (default: 10 messages) to understand who is talking to whom and roast with contextual precision.
- **Autonomous Chime-In Engine:** Periodically interrupts conversations based on a configurable probability (`CHIME_CHANCE=0.12`) and channel cooldown (`COOLDOWN_SECONDS=45`).
- **Channel Whitelisting:** Restrict autonomous roasts to specific channels, or leave blank to monitor all channels the bot can view.
- **$0 Free 24/7 Hosting:** Designed to run 24/7 for free on Render (Background Worker) with Groq Cloud's generous free tier.

---

## Prerequisites

1. **Discord Account** with permission to create applications and invite bots to a server.
2. **Groq Cloud API Key:** Free $0 API key from [Groq Console](https://console.groq.com/keys).
3. **Python 3.12+** (for local execution) or **Docker** / **Render Account**.

---

## Discord Bot Setup Guide

### Step 1: Create Discord Application & Bot
1. Navigate to the [Discord Developer Portal](https://discord.com/developers/applications).
2. Click **New Application** (top right), name it `Misskimo`, and agree to terms.
3. On the left sidebar, click **Bot**.
4. Click **Reset Token** to generate a new Bot Token. Copy this token—you will need it for `DISCORD_TOKEN`.

### Step 2: Enable Privileged Gateway Intents (CRITICAL)
> [!CAUTION]
> **MESSAGE CONTENT INTENT is REQUIRED!**
> Discord does not send message text to bots without this intent enabled. If omitted, Misskimo will see empty messages and cannot respond or roast.

1. Under **Bot** -> scroll down to **Privileged Gateway Intents**.
2. Toggle **MESSAGE CONTENT INTENT** to **ON** (checked).
3. (Optional but recommended) Ensure **SERVER MEMBERS INTENT** is also checked.
4. Click **Save Changes** at the bottom.

### Step 3: Generate Bot Invite URL
1. On the left sidebar, go to **OAuth2** -> **URL Generator**.
2. Under **Scopes**, select:
   - `bot`
   - `applications.commands` (REQUIRED for `/grouptalk` slash command)
3. Under **Bot Permissions**, select:
   - `Send Messages`
   - `Send Messages in Threads`
   - `Read Messages/View Channels`
   - `Read Message History`
4. Copy the generated **Invite URL** at the bottom of the page.
5. Paste the URL into your browser, select your server, and click **Authorize**.

Or use this pre-configured 1-click invite link:
👉 **[Invite Misskimo (with Slash Commands)](https://discord.com/oauth2/authorize?client_id=1573415000280797336&permissions=274877975552&scope=bot%20applications.commands)**


---

## Configuration Reference

Configure Misskimo via environment variables or a `.env` file:

| Variable | Required | Default | Description |
| :--- | :---: | :---: | :--- |
| `DISCORD_TOKEN` | **Yes** | — | Bot token from Discord Developer Portal. |
| `GROQ_API_KEY` | **Yes** | — | API key from [console.groq.com](https://console.groq.com/keys). |
| `GROQ_MODEL` | No | `qwen/qwen3.8-27b` | Groq model identifier for roast completions. |
| `ALLOWED_CHANNEL_IDS` | No | `""` (empty) | Comma-separated channel IDs. Empty allows all channels. |
| `CHIME_CHANCE` | No | `0.12` | Probability (0.0 to 1.0) of chiming in on unprompted messages. |
| `COOLDOWN_SECONDS` | No | `45` | Minimum seconds between autonomous roasts per channel. |
| `MAX_HISTORY_MESSAGES`| No | `10` | Number of recent messages retained for context. |

---

## Local Setup & Development

### 1. Clone & Set Up Virtual Environment

```bash
git clone https://github.com/your-username/misskimo-bot.git
cd misskimo-bot

# Create and activate virtual environment
python3.12 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
```
Edit `.env` and fill in your `DISCORD_TOKEN` and `GROQ_API_KEY`.

### 3. Run the Bot

```bash
python main.py
```

You should see logs indicating Misskimo is connected:
```
2026-11-21 00:30:00 [INFO] misskimo: Starting Misskimo Discord Bot...
2026-11-21 00:30:02 [INFO] misskimo.bot: Misskimo logged in as Misskimo#1234
```

---

## Docker Deployment

Build and run with Docker:

```bash
# Build the Docker image
docker build -t misskimo-bot .

# Run container with environment file
docker run -d \
  --name misskimo \
  --restart unless-stopped \
  --env-file .env \
  misskimo-bot
```

---

## 24/7 Free Hosting on Render

You can host Misskimo 24/7 completely free on Render using a **Background Worker**:

### Option A: 1-Click Blueprint (Recommended)
1. Fork or push this repository to your GitHub account.
2. Sign in to [Render](https://render.com).
3. In the Render Dashboard, click **New +** -> **Blueprint**.
4. Connect your GitHub repository. Render will automatically detect `render.yaml`.
5. Enter your `DISCORD_TOKEN` and `GROQ_API_KEY` when prompted.
6. Click **Apply**. Misskimo will build and run continuously in the background!

### Option B: Manual Background Worker
1. In Render Dashboard, click **New +** -> **Background Worker**.
2. Connect your repository.
3. Set the following settings:
   - **Name:** `misskimo-discord-bot`
   - **Runtime:** `Python`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python main.py`
4. Under **Environment Variables**, add:
   - `DISCORD_TOKEN` = `<your_discord_bot_token>`
   - `GROQ_API_KEY` = `<your_groq_api_key>`
   - `GROQ_MODEL` = `qwen/qwen3.8-27b`
   - `CHIME_CHANCE` = `0.12`
   - `COOLDOWN_SECONDS` = `45`
5. Click **Create Background Worker**.

---

## Testing

Run the comprehensive test suite (unit + integration):

```bash
.venv/bin/pytest tests/ -v
```

All tests are mock-isolated—no active Discord connection or Groq API credits are required during test execution.

---

## License

MIT
