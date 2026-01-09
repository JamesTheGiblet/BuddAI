# BuddAI: Your Personal AI Exocortex

> **A local code generator that remembers your corrections and gets better every time you use it.**

[![Tests](https://img.shields.io/badge/tests-129%20passing-brightgreen)]()
[![Accuracy](https://img.shields.io/badge/ESP32%20accuracy-90%25-blue)]()
[![License](https://img.shields.io/badge/license-MIT-blue)]()
[![Version](https://img.shields.io/badge/version-v4.0-purple)]()

---

## What BuddAI Can Do, and Why It Matters

BuddAI started as a simple idea: a local tool that remembers the corrections you teach it and applies those patterns to future code. No cloud training, no hype — just a system that improves the more you use it.

### What it can do today:
- Generate embedded-systems code with around 90% accuracy on ESP32 (validated over 14 hours)
- Store your corrections permanently and reuse them automatically
- Apply hardware-specific validation rules to catch common mistakes
- Improve its output every time you correct it (+40-60% per iteration in testing)
- Run fully local with no data leaving your machine

### Where it's heading:
- Support for multiple boards (ESP32 family, Arduino, STM32, Pico)
- Hundreds to thousands of learned patterns from real use
- Expanded validators for protocols, sensors, safety, and domain-specific rules
- Higher accuracy across more hardware as the pattern library grows
- A system that becomes faster and more reliable the longer you work with it

### Why this matters:

Most AI tools don't learn from you. They reset every session, forget your corrections, and generate generic output. BuddAI does the opposite — it keeps everything you teach it and builds on that knowledge over time.

The more you use it, the more it reflects your own approach, your hardware experience, and your problem-solving patterns. That compounding effect is where the real value comes from.

---

## Quick Start (10 Minutes)

### 1. Install Ollama
```bash
# Download from https://ollama.com
# One-click installer
```

### 2. Pull the Model
```bash
ollama serve  # Keep running in background

# In new terminal:
ollama pull qwen2.5-coder:3b    # ~2GB download
```

### 3. Get BuddAI
```bash
git clone https://github.com/JamesTheGiblet/BuddAI
cd BuddAI
```

### 4. Run It
```bash
# Terminal mode
python buddai_executive.py

# Or web interface (recommended)
python buddai_server.py --server
# Open http://localhost:8000/web
```

### 5. First Build
```
You: Generate ESP32-C3 motor driver with L298N

BuddAI: [Generates complete code]
        ✅ Pin definitions (auto-added)
        ✅ Safety timeout (auto-added)
        ✅ Your coding style applied
```

**That's it. You're running.**

---

## How It Actually Works

### The Learning Loop

**Example: Teaching BuddAI once saves forever**

```
Step 1: Generate code
You: "Generate servo control"
BuddAI: Uses analogWrite(pin, value);  // ❌ Wrong for ESP32

Step 2: Correct it
You: /correct ESP32 uses ledcWrite, not analogWrite
BuddAI: ✅ Stored in database

Step 3: Every future generation
BuddAI: Uses ledcWrite(channel, value);  // ✅ Automatic
```

**That correction is permanent.** You taught it once. It applies forever.

---

### The Architecture (No Magic)

```
User Request
    ↓
Load recent corrections from SQLite
    ↓
Inject into prompt as context
    ↓
Call local LLM (Qwen 2.5 Coder)
    ↓
Validate with 8 hardware-specific validators
    ↓
Auto-fix common issues
    ↓
Return clean code
```

**Simple but effective:**
- Database stores your corrections
- Prompt engineering injects them as context
- Validators catch hardware-specific mistakes
- LLM generates code following YOUR patterns

---

## Proven Performance

### 90% Accuracy (Validated)

14-hour comprehensive test across 10 questions:

```
Q1:  PWM LED Control         98%  ⭐
Q2:  Button Debouncing       95%  ⭐
Q3:  Servo Control           89%  ✅
Q4:  Motor Driver (L298N)    90%  ⭐
Q5:  State Machine           90%  ⭐ (30%→90% after teaching)
Q6:  Battery Monitoring      90%  ⭐
Q7:  LED Status Indicator    90%  ⭐
Q8:  Forge Theory            90%  ⭐
Q9:  Multi-Module System     80%  ✅
Q10: Complete GilBot         85%  ⭐

AVERAGE: 90% 🏆
```

**Full validation report:** [VALIDATION_REPORT.md](VALIDATION_REPORT.md)

---

### Time Savings (Measured)

**Traditional development:**
```
Research:  30 min
Code:      60 min
Debug:     60 min
Total:     150 min per module
```

**With BuddAI:**
```
Generate:  1 min
Review:    10 min
Fix:       10 min
Test:      30 min
Total:     51 min per module

SAVINGS: 99 minutes (66% faster)
```

**GilBot project:** 30 hours manual → 8.7 hours with BuddAI (71% savings)

---

## The 8 Validators

**What protects your code:**

1. **ESP32 Hardware** - Catches `analogWrite()`, wrong ADC resolution (4095 not 1023)
2. **Motor Control** - Prevents PWM conflicts, ensures L298N pins defined
3. **Timing Safety** - Requires safety timeouts, prevents `delay()` in motor loops
4. **Forge Theory** - Suggests exponential smoothing for fluid movement
5. **Servo/Combat** - Enforces state machines for weapon systems
6. **Arduino Compat** - Removes unnecessary includes, checks initialization
7. **Memory Safety** - Removes unused variables
8. **Style Guide** - Prevents feature bloat, enforces naming conventions

**29 checks total. Every generation protected.**

Full guide: [VALIDATOR_GUIDE.md](VALIDATOR_GUIDE.md)

---

## Essential Commands

```bash
/correct <why>  # Teach BuddAI the right way
/learn          # Extract patterns from corrections
/good           # Mark response as correct
/rules          # Show all learned patterns
/validate       # Check generated code
/metrics        # Show accuracy stats
```

### The Learning Loop
```
1. Generate code
2. Review (usually 85-95% correct)
3. If wrong: /correct <explanation>
4. Run /learn to extract patterns
5. Next generation: automatically improved

Typical: 1-3 iterations to perfection
Your effort: 5-15 min teaching
Result: Permanent improvement
```

---

## Current Capabilities

### ✅ What Works NOW

- ESP32-C3 firmware (90% accuracy)
- Hardware-specific validation
- Persistent correction database
- Auto-fix for common errors
- 100% local execution
- Web + terminal interfaces
- Remote access (Tailscale/Ngrok)

### ⚠️ Known Limitations

- **Domain-specific:** Best for embedded systems (trained on ESP32)
- **Requires training:** Fresh install starts at 60-70%, needs YOUR corrections
- **Model constraints:** 3B parameter model (fast but limited)
- **Session persistence:** Loads recent rules, not all patterns

**Future improvements:** Load all patterns on startup, fine-tune on YOUR corrections

---

## Why Local Matters

```
Cloud AI:           BuddAI:
💰 $20-200/month   ✅ FREE forever
🚫 Filtered        ✅ No restrictions
📡 Data mined      ✅ Never leaves your PC
⏱️ Rate limits     ✅ Unlimited
🌐 Internet needed ✅ Works offline
```

**Your hardware. Your network. Your data. YOUR control.**

---

## Honest Comparisons

### vs GitHub Copilot

**Copilot wins:**
- Better out-of-box (trained on billions of lines)
- Faster (no local model)
- IDE integration

**BuddAI wins:**
- YOUR corrections persist forever
- Hardware-specific validators
- 100% local, 100% private
- Learns YOUR patterns, not generic code

**Verdict:** Copilot for general coding. BuddAI for YOUR embedded domain after training.

---

### vs ChatGPT/Claude

**ChatGPT/Claude wins:**
- Smarter base model
- Broader knowledge
- Better at novel problems

**BuddAI wins:**
- Remembers YOUR corrections forever
- No monthly cost
- Hardware validation built-in
- Offline capable

**Verdict:** ChatGPT for new problems. BuddAI for repetitive work in YOUR domain.

---

## The Compounding Effect

### Month 1
```
Patterns: 244 → 330
Boards: ESP32-C3
Accuracy: 90%
```

### Month 3
```
Patterns: 330 → 600
Boards: ESP32-C3, Arduino, STM32
Accuracy: 90-92%
```

### Month 6
```
Patterns: 600 → 1,000+
Boards: 6+ platforms
Accuracy: 92-95%
Validators: 8 → 15
```

**Every correction compounds. Every pattern persists. Every day it gets better.**

---

## Documentation

- **[README.md]** - This file (quick start & overview)
- **[EVOLUTION.md]** - The v3.8 → v4.0 journey & theory
- **[VALIDATION_REPORT.md]** - 14 hours of testing results
- **[VALIDATOR_GUIDE.md]** - 8 validators, 29 checks explained
- **[TESTING_SUMMARY.md]** - 129 tests explained
- **[REMOTE_ACCESS_LOG.md]** - Remote access setup guide

---

## Privacy & Security

**100% Local:**
- Runs on your machine
- No cloud API calls (except optional fallback)
- No telemetry, no tracking

**Your IP Protected:**
- Code indexed locally
- Patterns stored locally (SQLite)
- Conversations local only
- Nothing ever leaves your PC

**Open Source MIT:**
- Code is public (audit anytime)
- YOUR data is private (never shared)
- No lock-in, you own everything

---

## Who This Is For

### ✅ Perfect If You:

- Build embedded systems
- Value cognitive freedom
- Want to own your tools
- Learn by doing
- Have YOUR patterns to preserve
- Work offline frequently

### ⚠️ Not For You If You:

- Need general-purpose coding (use ChatGPT)
- Want zero setup (cloud is easier)
- Don't have code to train on
- Prefer renting tools monthly

---

## Contributing

**Your BuddAI instance is unique:**
- Yours trains on YOUR repos
- Mine trains on MY repos
- Each becomes specialized

**To build YOUR exocortex:**
1. Index YOUR repositories
2. Teach YOUR patterns
3. Build YOUR projects
4. Watch it learn YOUR style

**To contribute to core:**
```bash
git clone https://github.com/JamesTheGiblet/BuddAI
cd BuddAI
pip install -r requirements.txt
python -m pytest tests/
```

---

## License

**MIT License** - Copyright (c) 2025-2026 James Gilbert / Giblets Creations

**The paradox:**
By making the code completely open, YOUR version becomes completely unreplicatable.

The value isn't the code (free forever).  
The value is YOUR training data (6 months of corrections, 1,000+ patterns, YOUR methodologies).

---

## Status

**Current:** v4.0  
**Tests:** 129/129 passing  
**Accuracy:** 90% (ESP32, validated)  
**Patterns:** 244 learned  
**Validators:** 8 active, 29 checks  

**Philosophy:** Not replacing you. Multiplying you. YOU × AI = 10x capability.

---

## Quick Links

- **Repository:** [github.com/JamesTheGiblet/BuddAI](https://github.com/JamesTheGiblet/BuddAI)
- **Creator:** [@JamesTheGiblet](https://github.com/JamesTheGiblet)
- **Organization:** [ModularDev-Tools](https://github.com/ModularDev-Tools)

---

**Ready to build YOUR cognitive extension?**

```bash
git clone https://github.com/JamesTheGiblet/BuddAI
cd BuddAI
python buddai_server.py --server
```

**Your journey to 10x capability starts now.** ⚡
