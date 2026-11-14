from __future__ import annotations

# Threat / bullying / coercion language → Critical.
CRITICAL_TERMS = (
    "threat",
    "threaten",
    "blackmail",
    "extort",
    "bully",
    "bullying",
    "abuse",
    "abusive",
    "harass",
    "harm",
    "hurt you",
    "kill",
    "murder",
    "shoot",
    "stab",
    "bomb",
    "suicide",
    "rape",
    "sexual",
    "or else",
    "pay or",
    "you will regret",
    "ruin you",
    "destroy you",
    "expose you",
    "leak your",
    "your photos",
    "fraud",
    "scam",
    "phishing",
)

# Rude / angry / hostile-but-not-threatening language → Attention.
ATTENTION_TERMS = (
    "angry",
    "anger",
    "furious",
    "mad",
    "rude",
    "insult",
    "disrespect",
    "shut up",
    "idiot",
    "stupid",
    "fool",
    "moron",
    "aggressive",
    "hostile",
    "yell",
    "shout",
    "screaming",
    "argument",
    "argue",
    "quarrel",
    "dispute",
    "unacceptable",
    "warning",
    "warned",
    "frustrated",
    "annoyed",
    "upset",
)


def classify_severity(*parts: str | None) -> str:
    """Return critical / warning / info from event or evidence text."""
    text = " ".join(part for part in parts if part).lower()
    if not text.strip():
        return "info"
    if any(term in text for term in CRITICAL_TERMS):
        return "critical"
    if any(term in text for term in ATTENTION_TERMS):
        return "warning"
    return "info"
