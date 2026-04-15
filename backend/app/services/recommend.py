import anthropic
import logging
from typing import List

from app.models.route import ComposedRoute

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "You are a concise travel advisor. When given a list of route options between two cities, "
    "write a 2–3 sentence recommendation that highlights the key trade-offs, uses specific "
    "numbers from the data, and gives a clear suggestion. "
    "Reply with just the recommendation text — no labels, no intro, no markdown."
)


def _summarise_routes(routes: List[ComposedRoute]) -> str:
    lines = []
    for r in routes:
        cost = f"${r.total_cost_usd:.0f}" if r.total_cost_usd > 0 else "cost unknown"
        h, m = divmod(r.total_duration_minutes, 60)
        duration = f"{h}h {m}m" if h else f"{m}m"
        tags = f" [{', '.join(r.tags)}]" if r.tags else ""
        lines.append(f"- {r.label}: {cost}, {duration}, {r.transfers} transfer(s){tags}")
    return "\n".join(lines)


async def generate_recommendation(
    routes: List[ComposedRoute],
    origin: str,
    destination: str,
    api_key: str,
) -> str:
    if not api_key:
        return ""

    client = anthropic.AsyncAnthropic(api_key=api_key)
    routes_text = _summarise_routes(routes)

    try:
        message = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=180,
            system=[
                {
                    "type": "text",
                    "text": _SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Routes from {origin} to {destination}:\n"
                        f"{routes_text}\n\n"
                        "What do you recommend?"
                    ),
                }
            ],
        )
        return message.content[0].text.strip()
    except Exception as exc:
        logger.warning("Recommendation generation failed: %s", exc)
        return ""
