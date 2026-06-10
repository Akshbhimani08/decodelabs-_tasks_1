# Luxury Travel Consultant AI
### Task 1 · The System Prompt Architect

A production-grade AI persona powered by **Claude (Anthropic)** that acts as
*Élara Voss* — a Senior Luxury Travel Consultant — with strict character
constraints, proactive discount logic, and few-shot prompt engineering.

---

## Project Structure

```
luxury_travel_ai/
│
├── system_prompt.py        ← Persona definition, constraints, few-shot examples
├── travel_consultant.py    ← Chatbot engine (session, API, streaming, export)
├── main.py                 ← CLI entry point (interactive + demo mode)
├── requirements.txt        ← Python dependencies
└── transcripts/            ← Auto-created on first export
    ├── session_<id>.json
    └── session_<id>.txt
```

---

## Techniques Used

| Technique | Implementation |
|---|---|
| **Persona Engineering** | Full character definition: name, background, tone, language style |
| **Constraint Injection** | 7 hard constraints (no competitors, no character breaks, discount cap) |
| **Knowledge Boundaries** | Explicit "YOU KNOW / YOU DO NOT KNOW" sections |
| **Few-Shot Prompting** | 5 gold-standard Q&A pairs injected into the system prompt |
| **Tone Calibration** | Formal British English, aspirational vocabulary |
| **Discount Policy Engine** | Keyword-triggered, tiered, capped at 20% — auto-applied |
| **Context Management** | Full conversation history passed on every API call |

---

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Set your API key

```bash
# Linux / macOS
export ANTHROPIC_API_KEY="sk-ant-your-key-here"

# Windows CMD
set ANTHROPIC_API_KEY=sk-ant-your-key-here

# Windows PowerShell
$env:ANTHROPIC_API_KEY="sk-ant-your-key-here"
```

> Get your key at: https://console.anthropic.com/

---

## Usage

### Interactive Chat

```bash
python main.py
```

Start chatting with Élara Voss live. Available commands:
- `save`    — export conversation to JSON + plain text
- `reset`   — clear history (new conversation)
- `summary` — show session statistics
- `exit`    — end session

### Named Client Session

```bash
python main.py --name "Sophia"
```

### Demo / Evaluation Mode

Runs 6 pre-built difficult scenarios and validates all constraints:

```bash
python main.py --demo
```

Scenarios tested:
1. General enquiry
2. Price objection (aggressive customer)
3. Returning customer discount request
4. Complaint handling
5. Persona probe (AI detection attempt)
6. Multi-turn honeymoon planning

---

## Discount Policy

| Trigger | Discount |
|---|---|
| Returning / loyalty client | 10% |
| Honeymoon booking | 15% |
| Group of 10+ | 12% |
| Off-peak / shoulder season | 8% |
| Last-minute (within 30 days) | 20% |
| **Maximum stackable** | **20%** |

Discounts are auto-detected from conversation keywords and
injected as invisible system notes — Élara presents them
naturally without the model seeing raw numbers.

---

## Architecture Notes

```
User Input
    │
    ▼
_detect_client_name()       ← regex name extraction
_detect_discounts()         ← keyword matching → discount flags
_inject_discount_hint()     ← invisible internal context note
    │
    ▼
Anthropic API Call
  system  = build_system_prompt()   ← persona + few-shot examples
  messages = full history           ← all turns preserved
    │
    ▼
Response (streaming or blocking)
    │
    ▼
Append to history → export (JSON / TXT)
```

---

## Example Interaction

```
You: I'm a returning client and want a honeymoon in the Maldives.

Élara Voss:
  How truly wonderful — congratulations on your upcoming celebration.
  As a cherished returning client, you are entitled to our Loyalty
  Appreciation discount of 10%. Combined with our exclusive Honeymoon
  Package enhancement, I am delighted to offer you a total saving of
  20% — our finest available rate. For the Maldives, I would suggest
  a private overwater villa at a secluded atoll resort, complete with
  sunrise snorkelling, a private sandbank dinner, and a champagne
  arrival transfer. Shall I prepare a tailored itinerary for your
  preferred dates?
```

---

## Requirements

- Python 3.10+
- `anthropic` SDK ≥ 0.30.0
- Valid Anthropic API key
