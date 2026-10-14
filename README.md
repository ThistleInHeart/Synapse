# ⚡ SYNAPSE — AI Neural Bridge for The Sims 4

[![Version](https://img.shields.io/badge/version-0.9.2--Pre--Release-blue.svg)](https://github.com)
[![Game](https://img.shields.io/badge/The%20Sims%204-PC%20%7C%20Mac-green.svg)](https://www.ea.com/games/the-sims/the-sims-4)
[![License](https://img.shields.io/badge/license-Source--Available%20%2B%20CC%20BY--NC--ND%204.0-orange.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/)

Next-generation neural ecosystem for **The Sims 4**: native game script mods coupled with the standalone **Synapse Bridge** desktop application (`Synapse.exe` / `ai_bridge.py`).

Free · Cloud APIs & Local GPUs · Modular Architecture · Beta v0.9.2

---

## 📖 Overview

**Synapse** is an advanced AI integration engine that bridges **The Sims 4** with modern Large Language Models (LLMs). The mod monitors hundreds of real-time game parameters every second—emotions, motives, occult states, environmental factors, relationships, pregnancy, and active interactions—and feeds this rich contextual picture to the AI.

There are no pre-scripted lines or canned responses. Every thought, face-to-face dialogue turn, and text message is generated from scratch in real time, reflecting the unique personality, history, and current situation of your Sims.

---

## 🧠 Core Modules

### 💭 1. AI Mind Reader (Stream of Consciousness)
* **Age & Psychology:** Distinct internal monologues tailored to life stages—from toddler babble and simple concepts to cynical teenage venting and adult responsibilities.
* **Occults & Supernatural Forms:** 
  * **Vampires:** Thirst for plasma, dark form awareness, arrogance toward mortals.
  * **Werewolves:** Pack instincts, rage levels, beast form status.
  * **Spellcasters:** Spellcraft reflections, magical charge.
  * **Aliens:** Disguise detection, secret origins.
  * **Ghosts:** Cause of death reflections.
  * **Plantsims:** Photosynthesis and plant nature.
* **Pets:** Cats, dogs, and horses experience the world through their own animal perspective.
* **Environmental Reactivity:** Moods, active outfits, nudity, pregnancy, fame level, weather, seasons, holidays, neighbors, jealousy, and intimate mod events (WickedWhims integration).
* **Autonomous Thoughts:** Sims think for themselves on an autonomous timer or on-demand via the pie menu.

### 🗣️ 2. Direct Dialogue (Face-to-Face Interaction)
* **Natural Language Speech:** Approach any Sim and type any dialogue line—the Sim evaluates the context, relationship scores, their traits, and responds aloud.
* **Smart Game Pause:** The game can automatically pause during AI generation with a clean status notification, ensuring the conversation partner doesn't walk away mid-reply.
* **Contextual Turn-Taking:** Remembers recent conversation history and topic flow.

### 💻 3. AI Social PC & Messenger
* **Direct Messaging:** Chat with friends, coworkers, and lovers from any in-game computer or smartphone.
* **Group Chats:** Create or join dynamic group chats with multiple Sims discussing daily events, school, or gossip.
* **Autonomous Incoming Messages:** Friends and acquaintances can text your Sim spontaneously to check in, invite them out, or share news.

### ⚡ 4. Interactive Action Tag System (`[WHODO=X]`, `[DO=Z]`)
* **AI-Driven Game Actions:** The AI can trigger actual in-game actions directly from dialogue text:
  * **Visiting Homes:** Characters can agree to visit your Sim's house after a chat.
  * **Joint Outings:** Travel together to other venues or lots.
  * **Romance & Physical Intimacy:** Automatically transition into romantic interactions or intimate scenes based on dialogue progress.
  * **Friendly & Hostile Interactions:** Hugs, arguments, gifts, or fights triggered organically by conversation flow.

### 🧠 5. Dynamic Long-Term Memory
* Significant moments, confessions, promises, and emotional shifts are permanently written to long-term memory files (`ai_social_memories.json`). Sims remember past conversations across play sessions.

---

## 📦 Repository Structure

```text
├── Synapse/                      # Standalone Bridge application & launcher
│   ├── Synapse.exe               # Graphical configuration launcher (GUI)
│   ├── ai_bridge.exe             # High-performance local bridge executable
│   ├── ai_bridge.py              # Open-source bridge HTTP server (127.0.0.1:8765)
│   ├── launcher.py               # Open-source CustomTkinter launcher interface
│   ├── localization_manager.py   # Translation and locale loader
│   ├── requirements.txt          # Python dependencies for pure-script execution
│   └── languages/                # Application UI and system prompt localizations
│       ├── EN.txt                # English language & prompts
│       └── RU.txt                # Russian language & prompts
│
├── SynapseMod/                   # Game mod files for The Sims 4
│   ├── Synapse_Interactions.package    # In-game pie menus, UI strings & tunings
│   ├── Synapse_SimMind.ts4script       # Mind Reader & perception engine
│   ├── Synapse_SocialMessenger.ts4script # Direct dialogue, messenger & memory
│   └── languages/mod_strings/          # In-game string table translations
│       ├── HOW_TO_TRANSLATE.txt        # Localization instructions for modders
│       ├── mod_strings_en.json         # English in-game strings
│       └── mod_strings_ru.json         # Russian in-game strings
│
├── LICENSE                       # Synapse License and Terms of Use (v0.3)
└── README.md                     # Project documentation
```

---

## 🚀 Installation & Setup

### Step 1. Install the Mod in The Sims 4
1. Copy the entire `SynapseMod/` folder into your The Sims 4 Mods directory:
   ```text
   Documents\Electronic Arts\The Sims 4\Mods\SynapseMod\
   ```
2. In The Sims 4 game settings (*Game Options → Other*), make sure both are checked:
   * **Enable Custom Content and Mods**
   * **Script Mods Allowed**
3. Restart the game if it was running.

### Step 2. Launch Synapse Bridge
You can start Synapse using either the compiled executable or pure Python source code:

#### Option A: Standalone Launcher (Recommended)
1. Navigate to the `Synapse/` directory and run **`Synapse.exe`**.
2. Select your language, choose your AI provider, enter your API key (or configure your local model URL), and click **Start Synapse Bridge**.
3. Launch The Sims 4 and enjoy!

#### Option B: Run from Source (No .exe required)
If you prefer running directly from source code:
1. Ensure Python 3.8+ is installed.
2. Install dependencies:
   ```bash
   cd Synapse
   pip install -r requirements.txt
   ```
3. Run the launcher:
   ```bash
   python launcher.py
   ```
   *(Or run the bridge directly: `python ai_bridge.py`)*

---

## 🌐 Supported AI Providers & Models

Synapse is provider-agnostic and connects to virtually any AI model:

| Provider | Supported Models / Notes |
| :--- | :--- |
| **OpenRouter** | DeepSeek V3/R1, Llama 3.3, Claude 3.5, Mistral, Gemma (Recommended) |
| **Google Gemini** | Gemini 2.0 Flash, Gemini 1.5 Pro (Fast & generous free tiers) |
| **OpenAI** | GPT-4o, GPT-4o-mini, o1, o3-mini |
| **Anthropic** | Claude 3.5 Sonnet, Claude 3.5 Haiku |
| **DeepSeek** | DeepSeek-V3, DeepSeek-R1 (Direct API) |
| **Groq** | Ultra-low latency Llama 3 models |
| **Local LLMs** | LM Studio, Ollama, vLLM, text-generation-webui (Zero cost, runs offline on your GPU) |

---

## 🛡️ Security, Privacy & Architecture

1. **Local Loopback Communication:**
   Communication between The Sims 4 script mod and the bridge application is strictly confined to your local machine via loopback address (`http://127.0.0.1:8765`). No external ports are opened.
2. **Native TLS / HTTPS:**
   Outgoing requests to AI providers use standard HTTPS and official Python networking libraries (`urllib3`). No proprietary tunneling or obscure wrappers.
3. **No `%TEMP%` Unpacking:**
   Both `Synapse.exe` and `ai_bridge.exe` operate in-place (`--onedir`), avoiding temporary file unpacking that often triggers false positives in antivirus heuristics.
4. **Source-Available:**
   All bridge logic (`ai_bridge.py`, `launcher.py`, `localization_manager.py`) is provided as readable Python source code alongside the executables.

---

## 🌍 Community Translations

Synapse features built-in multi-language support. Adding community translations is officially permitted and supported:
* **In-Game Strings:** Follow [`SynapseMod/languages/mod_strings/HOW_TO_TRANSLATE.txt`](SynapseMod/languages/mod_strings/HOW_TO_TRANSLATE.txt) to create standalone `.json` or `.package` translations.
* **Bridge Localization:** Create custom `[LANG].txt` files inside `Synapse/languages/` to translate the desktop UI and system prompts.
* Translators may distribute and monetize their standalone translation files in accordance with Section 1 of the [LICENSE](LICENSE).

---

## 📜 License & Terms of Use

Synapse is an independent, free project created by **Thistle**.

* **Creative Assets** (graphics, icons, UI design, texts, original prompts, presets, documentation) are licensed under the [Creative Commons Attribution-NonCommercial-NoDerivatives 4.0 International License (CC BY-NC-ND 4.0)](https://creativecommons.org/licenses/by-nc-nd/4.0/).
* **Software Code** (game mod, bridge application, launcher, scripts, and executable binaries) is governed by the project's custom Source-Available terms.
* Complete terms, permissions, exceptions for translators, and limitations of liability are set forth in the [LICENSE](LICENSE) file.

---

### Disclaimer
*Synapse is not affiliated with, sponsored, or endorsed by Electronic Arts Inc. or Maxis. The Sims and The Sims logos are trademarks of Electronic Arts Inc. This mod is provided free of charge in accordance with the EA User Agreement and EA Modding Policy.*
