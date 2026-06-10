"""
travel_consultant.py
────────────────────
Core chatbot engine for the Luxury Travel Consultant AI.

Features:
  • Session-based conversation management (full history preserved)
  • Anthropic Claude API integration (claude-sonnet-4-20250514)
  • Streaming support for real-time token output
  • Automatic discount eligibility detection
  • Conversation export (JSON + plain text transcript)
  • Graceful error handling with retry logic
"""

import json
import time
import re
import os
from datetime import datetime
from pathlib import Path
from typing import Generator

import anthropic

from system_prompt import build_system_prompt, DISCOUNT_POLICY



MODEL_ID          = "claude-sonnet-4-20250514"
MAX_TOKENS        = 1024
MAX_RETRIES       = 3
RETRY_DELAY_SEC   = 2
CONSULTANT_NAME   = "Élara Voss"
AGENCY_NAME       = "Lumière Voyages"

# Keywords that hint at discount eligibility — used for proactive suggestions
DISCOUNT_TRIGGERS = {
    "loyalty_returning":   ["returning", "last time", "again", "loyal", "previous trip", "came back"],
    "honeymoon_package":   ["honeymoon", "just married", "newlywed", "wedding trip"],
    "group_10_plus":       ["group", "team", "corporate", "family reunion", "10 people", "12 people"],
    "off_peak_shoulder":   ["shoulder season", "off peak", "off-peak", "avoid crowds", "quiet time"],
    "last_minute_30_days": ["last minute", "this month", "next week", "urgent", "asap"],
}




class TravelConsultantSession:
    """
    Manages a single client conversation session with Élara Voss.

    Attributes:
        client_name  : Detected or supplied client name (optional)
        history      : Full list of {"role": ..., "content": ...} message dicts
        session_id   : Unique identifier (timestamp-based)
        start_time   : datetime of session creation
        discount_flags: Set of triggered discount categories detected so far
    """

    def __init__(self, client_name: str = ""):
        self.client_name:   str   = client_name
        self.history:       list  = []
        self.session_id:    str   = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.start_time:    datetime = datetime.now()
        self.discount_flags: set  = set()
        self._system_prompt: str  = build_system_prompt()
        self._anthropic      = anthropic.Anthropic()   # reads ANTHROPIC_API_KEY from env

    # ── helpers ───────────────────────────────────────────────────────────────

    def _detect_discounts(self, user_message: str) -> list[str]:
        """
        Scans the user message for keywords that indicate discount eligibility.
        Returns a list of newly triggered discount category keys.
        """
        lower = user_message.lower()
        newly_triggered = []
        for category, keywords in DISCOUNT_TRIGGERS.items():
            if category not in self.discount_flags:
                if any(kw in lower for kw in keywords):
                    self.discount_flags.add(category)
                    newly_triggered.append(category)
        return newly_triggered

    def _detect_client_name(self, user_message: str) -> None:
        """
        Simple heuristic: looks for "I'm <Name>" or "My name is <Name>" patterns.
        Updates self.client_name if found and not already set.
        """
        if self.client_name:
            return
        patterns = [
            r"(?:i'?m|i am|my name is|call me)\s+([A-Z][a-z]+)",
            r"(?:this is)\s+([A-Z][a-z]+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, user_message, re.IGNORECASE)
            if match:
                self.client_name = match.group(1).strip()
                break

    def _inject_discount_hint(self, triggered: list[str]) -> str:
        """
        Builds a hidden context note appended to the user turn so the model
        knows which discounts are now applicable (without the user seeing it).
        """
        if not triggered:
            return ""
        hints = [
            f"{k.replace('_', ' ').title()}: {DISCOUNT_POLICY[k]}% eligible"
            for k in triggered
            if k in DISCOUNT_POLICY
        ]
        return (
            "\n\n[SYSTEM NOTE — INTERNAL — DO NOT REPEAT TO CLIENT]: "
            "The following discount(s) are now applicable for this client. "
            "Mention them naturally in your response: "
            + "; ".join(hints)
        )



    def chat(self, user_message: str, stream: bool = False):
        """
        Send a user message and receive the consultant's response.

        Args:
            user_message : The raw customer input string.
            stream       : If True, yields token chunks (generator).
                           If False, returns the full response string.

        Returns:
            str          : Full response (stream=False)
            Generator    : Token chunks  (stream=True)
        """
        # Analyse input
        self._detect_client_name(user_message)
        triggered = self._detect_discounts(user_message)
        hint      = self._inject_discount_hint(triggered)

        # Build the message with optional internal hint
        augmented_message = user_message + hint

        # Append to history
        self.history.append({"role": "user", "content": augmented_message})

        if stream:
            return self._stream_response()
        else:
            return self._blocking_response()

    def _blocking_response(self) -> str:
        """Calls the API and returns the complete response string."""
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                response = self._anthropic.messages.create(
                    model      = MODEL_ID,
                    max_tokens = MAX_TOKENS,
                    system     = self._system_prompt,
                    messages   = self.history,
                )
                assistant_text = response.content[0].text
                self.history.append({"role": "assistant", "content": assistant_text})
                return assistant_text

            except anthropic.RateLimitError:
                if attempt < MAX_RETRIES:
                    print(f"[Rate limit hit — retrying in {RETRY_DELAY_SEC}s …]")
                    time.sleep(RETRY_DELAY_SEC * attempt)
                else:
                    raise
            except anthropic.APIError as exc:
                raise RuntimeError(f"API error after {attempt} attempt(s): {exc}") from exc

    def _stream_response(self) -> Generator[str, None, None]:
        """Streams the API response and yields token chunks."""
        collected_text = []

        with self._anthropic.messages.stream(
            model      = MODEL_ID,
            max_tokens = MAX_TOKENS,
            system     = self._system_prompt,
            messages   = self.history,
        ) as stream:
            for chunk in stream.text_stream:
                collected_text.append(chunk)
                yield chunk

        full_text = "".join(collected_text)
        self.history.append({"role": "assistant", "content": full_text})



    def export_json(self, filepath: str | None = None) -> str:
        """
        Exports the full conversation as a structured JSON file.

        Args:
            filepath : Optional custom path. Defaults to
                       transcripts/session_<id>.json

        Returns:
            str : The filepath where the file was written.
        """
        if filepath is None:
            Path("transcripts").mkdir(exist_ok=True)
            filepath = f"transcripts/session_{self.session_id}.json"

        payload = {
            "session_id":    self.session_id,
            "client_name":   self.client_name or "Unknown",
            "agency":        AGENCY_NAME,
            "consultant":    CONSULTANT_NAME,
            "start_time":    self.start_time.isoformat(),
            "export_time":   datetime.now().isoformat(),
            "discounts_triggered": list(self.discount_flags),
            "message_count": len([m for m in self.history if m["role"] == "user"]),
            "conversation":  [
                {
                    "turn":    i + 1,
                    "role":    m["role"],
                    # Strip internal system notes before export
                    "content": m["content"].split("[SYSTEM NOTE")[0].strip(),
                }
                for i, m in enumerate(self.history)
            ],
        }
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)

        return filepath

    def export_transcript(self, filepath: str | None = None) -> str:
        """
        Exports the conversation as a human-readable plain-text transcript.

        Returns:
            str : The filepath where the file was written.
        """
        if filepath is None:
            Path("transcripts").mkdir(exist_ok=True)
            filepath = f"transcripts/session_{self.session_id}.txt"

        lines = [
            f"{'=' * 60}",
            f"  {AGENCY_NAME} — Client Conversation Transcript",
            f"{'=' * 60}",
            f"  Session ID  : {self.session_id}",
            f"  Client      : {self.client_name or 'Unknown'}",
            f"  Consultant  : {CONSULTANT_NAME}",
            f"  Date/Time   : {self.start_time.strftime('%d %B %Y, %H:%M')}",
            f"{'=' * 60}",
            "",
        ]

        for msg in self.history:
            role_label = (
                f"Client ({self.client_name})" if msg["role"] == "user" and self.client_name
                else "Client" if msg["role"] == "user"
                else f"Élara Voss [{AGENCY_NAME}]"
            )
            clean_content = msg["content"].split("[SYSTEM NOTE")[0].strip()
            lines.append(f"[{role_label}]")
            lines.append(clean_content)
            lines.append("")

        lines += [
            f"{'─' * 60}",
            f"  Discounts triggered : {', '.join(self.discount_flags) or 'None'}",
            f"  Messages exchanged  : {len([m for m in self.history if m['role'] == 'user'])}",
            f"{'─' * 60}",
        ]

        with open(filepath, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        return filepath

    def reset(self) -> None:
        """Clears conversation history while preserving session metadata."""
        self.history.clear()
        self.discount_flags.clear()

    def summary(self) -> dict:
        """Returns a brief session summary dictionary."""
        return {
            "session_id":     self.session_id,
            "client_name":    self.client_name or "Unknown",
            "turns":          len([m for m in self.history if m["role"] == "user"]),
            "discounts_live": list(self.discount_flags),
            "duration_mins":  round((datetime.now() - self.start_time).seconds / 60, 1),
        }



if __name__ == "__main__":
    print("[travel_consultant.py] Module loaded successfully.")
    print(f"Model       : {MODEL_ID}")
    print(f"Consultant  : {CONSULTANT_NAME}")
    print(f"Agency      : {AGENCY_NAME}")
    print(f"Discount tiers: {list(DISCOUNT_POLICY.keys())}")
