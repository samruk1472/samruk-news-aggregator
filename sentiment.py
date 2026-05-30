import os
import re

# Russian/Kazakh sentiment dictionaries
NEGATIVE_WORDS = {
    "авария", "кризис", "катастрофа", "ущерб", "убыток", "убытки", "потери", "потеря",
    "скандал", "коррупция", "мошенничество", "задержание", "арест", "обыск",
    "штраф", "санкции", "санкция", "долг", "задолженность", "банкротство",
    "авт катастрофа", "несчастный случай", "жертвы", "пострадавшие",
    "протест", "забастовка", "увольнение", "сокращение", "снижение",
    "падение", "обвал", "провал", "задержка", "нарушение", "нарушения",
    "загрязнение", "утечка", "взрыв", "пожар", "катастрофа", "трагедия",
    "конфликт", "спор", "иск", "претензия", "жалоба",
    "decline", "loss", "scandal", "corruption", "fraud", "arrest",
    "fine", "sanction", "debt", "bankruptcy", "accident", "disaster",
    "protest", "strike", "layoff", "reduction", "drop", "crash",
    "failure", "delay", "violation", "pollution", "explosion", "fire",
    "conflict", "dispute", "lawsuit", "complaint",
}

POSITIVE_WORDS = {
    "рост", "прибыль", "доход", "успех", "достижение", "рекорд",
    "инвестиции", "инвестиция", "партнёрство", "партнерство", "сотрудничество",
    "соглашение", "контракт", "победа", "награда", "признание",
    "развитие", "расширение", "запуск", "открытие", "модернизация",
    "улучшение", "повышение", "увеличение", "подъём", "рекордный",
    "инновации", "инновация", "экспорт", "дивиденды",
    "growth", "profit", "revenue", "success", "achievement", "record",
    "investment", "partnership", "cooperation", "agreement", "contract",
    "victory", "award", "recognition", "development", "expansion",
    "launch", "opening", "modernization", "improvement", "increase",
    "innovation", "export", "dividend",
}


def _count_words(text: str, word_set: set) -> int:
    text_lower = text.lower()
    return sum(1 for w in word_set if w in text_lower)


def classify_dictionary(text: str) -> str:
    neg = _count_words(text, NEGATIVE_WORDS)
    pos = _count_words(text, POSITIVE_WORDS)
    if neg > pos:
        return "negative"
    if pos > neg:
        return "positive"
    return "neutral"


def classify_claude(text: str, client) -> str:
    truncated = text[:2000]
    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=10,
        messages=[
            {
                "role": "user",
                "content": (
                    f"Classify the sentiment of this news article as exactly one word: "
                    f"'positive', 'neutral', or 'negative'. "
                    f"Article: {truncated}"
                ),
            }
        ],
    )
    result = message.content[0].text.strip().lower()
    if "positive" in result:
        return "positive"
    if "negative" in result:
        return "negative"
    return "neutral"


def classify(text: str, engine: str = "dictionary", client=None):
    if engine == "claude_api" and client:
        try:
            return classify_claude(text, client)
        except Exception:
            pass
    return classify_dictionary(text)


def generate_summary(title: str, text: str, engine: str = "dictionary", client=None):
    if engine == "claude_api" and client:
        try:
            truncated = text[:3000]
            message = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=100,
                messages=[
                    {
                        "role": "user",
                        "content": (
                            f"Напиши краткое резюме новости в 1-2 предложения на русском языке.\n"
                            f"Заголовок: {title}\n"
                            f"Текст: {truncated}"
                        ),
                    }
                ],
            )
            return message.content[0].text.strip()
        except Exception:
            pass
    # Fallback: return truncated title
    return title[:200]
