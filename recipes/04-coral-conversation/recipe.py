"""Recipe 04 — Long conversational context with Cohere.

Problem: Maintain context across many turns without blowing the context window.
Pattern: chat_history + periodic summarization.

Usage:
    python -m recipes.04-coral-conversation.recipe
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from common.client import CookbookClient  # noqa: E402


SYSTEM = (
    "You are a supportive thinking partner. Keep track of context across turns. "
    "When the user asks about something mentioned earlier, refer to it precisely."
)


class ConversationManager:
    """Maintains a rolling conversation with automatic summarization.

    When the conversation approaches the context window, old turns are
    replaced with a summary block preserving salient facts.
    """

    def __init__(
        self,
        client: CookbookClient,
        max_turns_before_summary: int = 20,
        model: str = "command-r-plus-08-2024",
    ) -> None:
        self.client = client
        self.max_turns = max_turns_before_summary
        self.model = model
        self.messages: list[dict] = []
        self.summary_block: str | None = None

    def user(self, text: str) -> str:
        """User message → assistant response."""
        turn_msgs: list[dict] = []
        if self.summary_block:
            turn_msgs.append(
                {
                    "role": "system",
                    "content": f"[Context summary from earlier]: {self.summary_block}",
                }
            )
        turn_msgs.extend(self.messages)
        turn_msgs.append({"role": "user", "content": text})

        result = self.client.send(
            messages=turn_msgs,
            model=self.model,
            preamble=SYSTEM,
        )

        self.messages.append({"role": "user", "content": text})
        self.messages.append({"role": "assistant", "content": result.text})

        if len(self.messages) >= self.max_turns:
            self._compress()

        return result.text

    def _compress(self) -> None:
        """Summarize the oldest half of messages into a single summary block."""
        half = len(self.messages) // 2
        old = self.messages[:half]

        summarize_prompt = (
            "Summarize this conversation fragment in under 200 words. "
            "Preserve: names, facts, decisions, open questions. Omit small talk."
        )
        old_text = "\n".join(f"{m['role']}: {m['content']}" for m in old)

        result = self.client.send(
            message=f"{summarize_prompt}\n\n---\n\n{old_text}",
            model=self.model,
        )

        if self.summary_block:
            self.summary_block += "\n\n" + result.text
        else:
            self.summary_block = result.text

        self.messages = self.messages[half:]

    def reset(self) -> None:
        self.messages = []
        self.summary_block = None


def main() -> int:
    client = CookbookClient()
    conv = ConversationManager(client, max_turns_before_summary=10)

    transcript = [
        "My name is Doeon. I'm working on agent reliability.",
        "What's the best way to measure tool-call success?",
        "Can you remind me what my name is?",
        "I'm thinking about switching from OpenAI to Cohere for RAG. Worth it?",
        "What did I say I'm working on?",
    ]

    for line in transcript:
        print(f"\nYou: {line}")
        reply = conv.user(line)
        print(f"Assistant: {reply}")

    if conv.summary_block:
        print(f"\n[Auto-summary generated:]\n{conv.summary_block}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
