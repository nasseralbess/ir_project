from spellchecker import SpellChecker
import re
import os
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

spell = SpellChecker()

ABBREVIATIONS = {
    "ai": "artificial intelligence",
    "ml": "machine learning",
    "nlp": "natural language processing",
    "cv": "computer vision",
    "dl": "deep learning",
}
SYNONYMS = {
    "ai": ["artificial intelligence", "machine intelligence"],
    "computer": ["computing", "pc"],
    "phone": ["mobile", "smartphone", "cellphone"],
    "internet": ["web", "online", "net"],
    "software": ["program", "application", "app"],
}

def parse_query(query: str) -> tuple[str, bool]:
    """Normalize case and clean punctuation. Returns (query, is_phrase)."""
    is_phrase = bool(re.search(r'"([^"]+)"', query))
    
    if is_phrase:
        match = re.search(r'"([^"]+)"', query)
        phrase = match.group(1).lower().strip()
        return phrase, True
    else:
        cleaned = re.sub(r"[^\w\s]", "", query.lower()).strip()
        return cleaned, False


def suggest_spelling(query: str) -> str:
    """Suggest spelling corrections for misspelled words."""
    words = query.split()
    corrected = []
    for w in words:
        if w not in spell:
            suggestion = spell.correction(w)
            corrected.append(suggestion if suggestion else w)
        else:
            corrected.append(w)
    return " ".join(corrected)

def expand_abbreviations(query: str) -> str:
    """Replace known abbreviations with their expanded forms."""
    words = query.split()
    expanded = [ABBREVIATIONS.get(w.lower(), w) for w in words]
    return " ".join(expanded)

def expand_query_with_synonyms(query: str) -> str:
    """Expand query with synonyms of key terms."""
    words = query.split()
    expanded_terms = []
    
    for word in words:
        expanded_terms.append(word)
        if word.lower() in SYNONYMS:
            expanded_terms.extend(SYNONYMS[word.lower()])
    
    return " ".join(expanded_terms)

def llm_query_expansion(query: str) -> str:
    with open("prompts/query_expansion.txt", "r") as f:
        prompt_template = f.read()

    client = Groq(api_key=os.getenv("GROQ_API_KEY"))

    chat_completion = client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": prompt_template.format(query=query),
            }
        ],
        model="openai/gpt-oss-20b",
    )
    return chat_completion.choices[0].message.content

