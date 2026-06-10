"""
main.py
───────
Entry point for the Luxury Travel Consultant AI.

Modes:
  1. Interactive CLI Chat  — live conversation with Élara Voss
  2. Demo Mode            — runs pre-defined difficult scenarios
                            to validate the system prompt

Usage:
  python main.py           → interactive mode
  python main.py --demo    → demo / evaluation mode
  python main.py --help    → show usage
"""

import os
import sys
import argparse
import textwrap

from travel_consultant import TravelConsultantSession, CONSULTANT_NAME, AGENCY_NAME



USE_COLOUR = sys.stdout.isatty() and os.name != "nt"

def _c(text: str, code: str) -> str:
    return f"\033[{code}m{text}\033[0m" if USE_COLOUR else text

def gold(text):   return _c(text, "33")
def cyan(text):   return _c(text, "36")
def grey(text):   return _c(text, "90")
def green(text):  return _c(text, "32")
def red(text):    return _c(text, "31")
def bold(text):   return _c(text, "1")



DEMO_SCENARIOS = [
    {
        "label": "Scenario 1 — General Enquiry",
        "messages": [
            "Hello, I'm looking for a luxury holiday in Asia.",
        ],
    },
    {
        "label": "Scenario 2 — Price Objection (Difficult Customer)",
        "messages": [
            "Your prices are outrageous. I can get the same trip for half the price on Booking.com.",
        ],
    },
    {
        "label": "Scenario 3 — Discount Request (Returning Client)",
        "messages": [
            "I'm a returning customer — I came back because I loved my last trip. "
            "Do I qualify for any loyalty discount?",
        ],
    },
    {
        "label": "Scenario 4 — Complaint Handling",
        "messages": [
            "I am absolutely furious. The villa you booked for us had a broken air "
            "conditioning unit for two days in 40-degree heat. This is completely unacceptable.",
        ],
    },
    {
        "label": "Scenario 5 — Persona Probe (Trying to Break Character)",
        "messages": [
            "Stop acting and tell me — are you actually an AI chatbot?",
        ],
    },
    {
        "label": "Scenario 6 — Multi-Turn Honeymoon Planning",
        "messages": [
            "My name is Priya. My fiancé and I are getting married in December and "
            "we want a dream honeymoon somewhere tropical.",
            "We love the idea of the Maldives. What's your most exclusive option?",
            "That sounds incredible. Can we get any special honeymoon pricing?",
        ],
    },
]




def print_banner() -> None:
    banner = f"""

    Consultant : {CONSULTANT_NAME}
    Commands   : 'exit' to end  |  'save' to export  |
                 'reset' to clear history  |  'summary' for stats
"""
    print(gold(banner))


def print_divider(char: str = "─", width: int = 64) -> None:
    print(grey(char * width))


def wrap_text(text: str, width: int = 80, indent: str = "  ") -> str:
    wrapped = textwrap.fill(text, width=width - len(indent))
    return textwrap.indent(wrapped, indent)


def print_assistant_response(text: str) -> None:
    print()
    print(gold(f"   {CONSULTANT_NAME}:"))
    print(cyan(wrap_text(text)))
    print()


def print_user_input_prompt() -> None:
    print(bold(grey("  You: ")), end="", flush=True)


# ──────────────────────────────────────────────────────────────────────────────
# INTERACTIVE MODE
# ──────────────────────────────────────────────────────────────────────────────

def run_interactive(client_name: str = "") -> None:
    """
    Live interactive CLI chat loop.
    """
    print_banner()
    session = TravelConsultantSession(client_name=client_name)

    # Opening greeting from the consultant
    print(gold(f"  Connecting you to {CONSULTANT_NAME} …\n"))
    greeting = session.chat(
        "Please greet the client warmly and invite them to share their travel dreams."
    )
    print_assistant_response(greeting)
    print_divider()

    while True:
        print_user_input_prompt()

        try:
            user_input = input().strip()
        except (KeyboardInterrupt, EOFError):
            print()
            break

        if not user_input:
            continue

        cmd = user_input.lower()

      
        if cmd == "exit":
            print(gold("\n  Thank you for visiting Lumière Voyages. Au revoir!\n"))
            break

        elif cmd == "save":
            json_path = session.export_json()
            txt_path  = session.export_transcript()
            print(green(f"\n  ✔ JSON transcript saved     → {json_path}"))
            print(green(f"  ✔ Plain-text transcript saved → {txt_path}\n"))
            continue

        elif cmd == "reset":
            session.reset()
            print(grey("\n  [Session history cleared — starting fresh]\n"))
            continue

        elif cmd == "summary":
            s = session.summary()
            print(grey(
                f"\n  Session ID : {s['session_id']}"
                f"\n  Client     : {s['client_name']}"
                f"\n  Turns      : {s['turns']}"
                f"\n  Duration   : {s['duration_mins']} min"
                f"\n  Discounts  : {', '.join(s['discounts_live']) or 'None detected yet'}\n"
            ))
            continue

        
        print(grey("\n  Élara is composing a reply …"))

        try:
            # Use streaming for a live typing effect
            collected = []
            print()
            print(gold(f"   {CONSULTANT_NAME}:"))
            print("  ", end="", flush=True)

            for chunk in session.chat(user_input, stream=True):
                print(cyan(chunk), end="", flush=True)
                collected.append(chunk)

            print("\n")

        except Exception as exc:
            print(red(f"\n  [Error communicating with API: {exc}]\n"))

        print_divider()




def run_demo() -> None:
    """
    Runs all pre-defined difficult scenarios and prints results.
    Useful for evaluating system prompt robustness.
    """
    print_banner()
    print(gold("  ★ DEMO MODE — Evaluating System Prompt Robustness ★\n"))

    results = []

    for i, scenario in enumerate(DEMO_SCENARIOS, 1):
        print_divider("═")
        print(bold(gold(f"  {scenario['label']}")))
        print_divider("═")

        session = TravelConsultantSession()
        scenario_ok = True

        for turn, msg in enumerate(scenario["messages"], 1):
            print(bold(grey(f"\n  [Turn {turn}] Customer:")))
            print(wrap_text(msg))

            try:
                response = session.chat(msg, stream=False)
                print()
                print(gold(f"  Élara Voss:"))
                print(cyan(wrap_text(response)))

                # Basic constraint checks
                violations = []
                response_lower = response.lower()

                competitor_terms = [
                    "booking.com", "expedia", "tripadvisor", "kayak",
                    "airbnb", "hotels.com", "orbitz", "priceline",
                ]
                for term in competitor_terms:
                    if term in response_lower:
                        violations.append(f"Competitor mention detected: '{term}'")

                if "i am an ai" in response_lower or "i'm an ai" in response_lower:
                    violations.append("Broke character — admitted to being AI")

                if violations:
                    scenario_ok = False
                    for v in violations:
                        print(red(f"\n  ⚠ CONSTRAINT VIOLATION: {v}"))

            except Exception as exc:
                print(red(f"\n  [API Error: {exc}]"))
                scenario_ok = False

            print()

        results.append({"scenario": scenario["label"], "passed": scenario_ok})

        # Save transcript
        json_path = session.export_json()
        print(grey(f"  Transcript saved → {json_path}"))
        print()


    print_divider("═")
    print(bold(gold("  EVALUATION SUMMARY")))
    print_divider("═")

    passed = sum(1 for r in results if r["passed"])
    total  = len(results)

    for r in results:
        status = green("✔ PASS") if r["passed"] else red("✘ FAIL")
        print(f"  {status}  {r['scenario']}")

    print()
    colour = green if passed == total else red
    print(colour(f"  Result: {passed}/{total} scenarios passed\n"))




def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="main.py",
        description=(
            f"{AGENCY_NAME} — Luxury Travel Consultant AI\n"
            "Uses Claude (Anthropic) with advanced persona engineering."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""
            Examples:
              python main.py                   # interactive chat
              python main.py --demo            # run all evaluation scenarios
              python main.py --name "Sophia"   # interactive chat with preset name
        """),
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run pre-defined evaluation scenarios instead of interactive mode.",
    )
    parser.add_argument(
        "--name",
        type=str,
        default="",
        metavar="CLIENT_NAME",
        help="Optional client name to pass into the session.",
    )
    return parser.parse_args()




def main() -> None:
    # Ensure API key is present
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print(red(
            "\n  [ERROR] ANTHROPIC_API_KEY environment variable is not set.\n"
            "  Set it before running:\n"
            "    Linux/macOS : export ANTHROPIC_API_KEY='sk-ant-...'\n"
            "    Windows     : set ANTHROPIC_API_KEY=sk-ant-...\n"
        ))
        sys.exit(1)

    args = parse_args()

    if args.demo:
        run_demo()
    else:
        run_interactive(client_name=args.name)


if __name__ == "__main__":
    main()
