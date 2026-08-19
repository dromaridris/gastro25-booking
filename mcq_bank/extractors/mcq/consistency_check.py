"""
Heuristic-only cross-check between a question's explanation text and its
book-stated correct answer. NEVER changes the answer - the book's stated
letter is always kept verbatim. This only raises a review flag when the
explanation's affirming language ('should be performed', 'is the most
appropriate', etc.) appears to line up more strongly with a different
option's wording than the option the book marked correct, so a human
reviewer can take a second look.
"""
import re

STOPWORDS = {
    "the", "a", "an", "of", "in", "on", "to", "and", "or", "is", "are", "was",
    "were", "with", "for", "by", "as", "at", "this", "that", "these", "those",
    "be", "would", "should", "not", "no", "than", "given", "based", "due",
    "next", "best", "most", "appropriate", "step", "option", "management",
    "patient", "patients", "case",
}

AFFIRMING_SENTENCE_RE = re.compile(
    r"(should be performed|should be (started|initiated|obtained|considered)|"
    r"would be (the )?(most appropriate|best|next best step|preferred|recommended)|"
    r"is (the )?(most appropriate|best|recommended|preferred|indicated)|"
    r"next best step (would be|is)|"
    r"recommend(ed|ation)?\b)",
    re.IGNORECASE,
)

NEGATION_GUARD_RE = re.compile(
    r"(\bnot\b|\bno\b|\bn't\b|\brarely\b|\bunlikely\b|\bwould not\b|\bdoes not\b|"
    r"\bdo not\b|\bdid not\b|\bif\b.*\b(suspected|were|was|present|indicated)\b|"
    r"\bwithout\b|\bcontraindicated\b)",
    re.IGNORECASE,
)


def _significant_words(text):
    words = re.findall(r"[a-zA-Z']+", text.lower())
    return {w for w in words if len(w) > 3 and w not in STOPWORDS}


def check_rationale_answer_consistency(rationale_text, option_texts, correct_letter):
    if not correct_letter or correct_letter not in option_texts:
        return None, {}

    sentences = re.split(r"(?<=[.!?])\s+", rationale_text)
    affirming_sentences = [
        s for s in sentences
        if AFFIRMING_SENTENCE_RE.search(s) and not NEGATION_GUARD_RE.search(s)
    ]
    if not affirming_sentences:
        return None, {}

    option_sig_words = {letter: _significant_words(text) for letter, text in option_texts.items()}
    scores = {letter: 0 for letter in option_texts}
    best_sentence_per_letter = {}

    for sent in affirming_sentences:
        sent_words = _significant_words(sent)
        for letter, sig_words in option_sig_words.items():
            overlap = len(sent_words & sig_words)
            if overlap > scores[letter]:
                scores[letter] = overlap
                best_sentence_per_letter[letter] = sent.strip()

    if not any(scores.values()):
        return None, {}

    top_letter = max(scores, key=lambda l: scores[l])
    top_score = scores[top_letter]
    correct_score = scores.get(correct_letter, 0)

    if top_letter != correct_letter and top_score >= 3 and top_score - correct_score >= 2:
        return "rationale_may_favor_different_option", {
            "book_states_correct": correct_letter,
            "rationale_language_favors": top_letter,
            "evidence_sentence": best_sentence_per_letter.get(top_letter, ""),
        }
    return None, {}
