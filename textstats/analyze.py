"""Core text-analysis functions for textstats.

Everything in this module is pure, deterministic and offline; only the
Python standard library is used. The metrics are deliberately simple,
plain-English approximations that are easy to reproduce by hand:

* **Sentences** end at a ``.``, ``!`` or ``?`` that is followed by
  whitespace (or the end of the input). A period inside an abbreviation
  such as ``Mr.`` is therefore treated as a sentence boundary, so ``Mr``
  becomes a one-word sentence. This is the documented simplification.
* **Words** are runs of letters, digits and apostrophes. Punctuation and
  whitespace (including en/em dashes) separate words. Words are
  lowercased for counting; stray leading/trailing apostrophes are dropped
  (``'the`` becomes ``the``, ``dogs'`` becomes ``dogs``).
* **Syllables** are counted by runs of vowel letters (``a e i o u y``),
  minus a silent trailing ``e`` (a final ``e`` after a consonant whose
  earlier vowel run is a single vowel letter). Examples: ``hello``=2,
  ``world``=1, ``python``=2, ``readability``=5, ``the``=1, ``maybe``=2,
  ``lovely``=3 (a known over-count). This is an approximation, not a
  dictionary.
* **Paragraphs** are blocks separated by one or more blank lines.

Readability formulas (``w`` words, ``s`` sentences, ``sy`` syllables,
``c`` complex words -- words of 3+ syllables under our rule, ``p``
polysyllable words):

* Flesch Reading Ease: 206.835 - 1.015*w/s - 84.6*sy/w
* Flesch-Kincaid Grade: 0.39*w/s + 11.8*sy/w - 15.59
* Gunning Fog: 0.4*(w/s + c/w)
* SMOG: 1.0430*sqrt(30*p/s) + 3.1291

Zero-denominator inputs (no sentences, no words) never produce NaN or
infinity: the functions floor the ``words`` and ``sentences``
denominators at 1 internally, so an empty text yields defined, finite
scores.
"""

import re
import string
from dataclasses import dataclass

__all__ = [
    "Analysis",
    "SENT_HIST_BUCKET",
    "WORD_HIST_MAX",
    "analyze",
    "flesch",
    "flesch_kincaid",
    "gunning_fog",
    "smog",
    "syllables",
    "tokenize_sentences",
    "tokenize_words",
]

_SENT_BOUNDARY = re.compile(r"[.!?](?=\s|$)")
_WORD = re.compile(r"[A-Za-z0-9']+")
_BLANK_LINE = re.compile(r"\n\s*\n")
_VOWELS = frozenset("aeiouy")

WORD_HIST_MAX = 12      # word-length bins 1..12, bin 12 is "12 or more"
SENT_HIST_BUCKET = 5    # sentence-length bins: 1-5, 6-10, 11-15, ...


def tokenize_sentences(text):
    """Split *text* into a list of sentence strings.

    A sentence ends at ``.`` ``!`` ``?`` that is followed by whitespace
    or the end of the input. Abbreviation periods (``Mr.``) therefore
    split too -- that is the documented simplification. Leftover edge
    punctuation is stripped and empty fragments are dropped.
    """
    sentences = []
    for part in _SENT_BOUNDARY.split(text or ""):
        cleaned = part.strip(string.punctuation).strip()
        if cleaned:
            sentences.append(cleaned)
    return sentences


def tokenize_words(sentence):
    """Split one *sentence* into lowercased word tokens.

    Words are runs of letters, digits and apostrophes. The result is
    lowercased for counting and stray edge apostrophes are removed.
    """
    words = []
    for raw in _WORD.findall((sentence or "").lower()):
        word = raw.strip("'")
        if word:
            words.append(word)
    return words


def _vowel_group_count(word):
    """Number of maximal runs of vowel letters in *word*."""
    groups = 0
    in_vowel = False
    for ch in word:
        if ch in _VOWELS:
            if not in_vowel:
                groups += 1
            in_vowel = True
        else:
            in_vowel = False
    return groups


def _last_vowel_group_len(word):
    """Length of the final maximal run of vowel letters in *word*."""
    last, current = 0, 0
    for ch in word:
        if ch in _VOWELS:
            current += 1
        else:
            if current:
                last = current
            current = 0
    if current:
        last = current
    return last


def syllables(word):
    """Return an approximate syllable count for *word*.

    The rule: count maximal runs of vowel letters (``a e i o u y``).
    A silent trailing ``e`` (a final ``e`` preceded by a consonant, when
    the word has an earlier vowel group whose final run is a single
    vowel letter that is not the ``y`` of a two-letter group like ``ay``)
    is subtracted. Words with no vowels count as one syllable.

    Hand examples: hello=2, world=1, python=2, readability=5, the=1,
    maybe=2, love=1, cake=1. ``lovely`` scores 3 -- a documented
    over-count of the approximation.
    """
    word = (word or "").lower()
    if not word:
        return 0
    count = _vowel_group_count(word) or 1
    if len(word) > 1 and word[-1] == "e" and word[-2] not in _VOWELS and count >= 2:
        remainder = word[:-1]
        if _vowel_group_count(remainder) >= 1 and _last_vowel_group_len(remainder) == 1:
            count -= 1
    return count if count > 0 else 1


def _denom(value):
    """Denominator floor: 0 becomes 1 so empty input stays NaN-free."""
    return value if value > 0 else 1


def flesch(words, sentences, syllable_total):
    """Flesch Reading Ease score (higher = easier to read)."""
    w, s = _denom(words), _denom(sentences)
    return 206.835 - 1.015 * (w / s) - 84.6 * (syllable_total / w)


def flesch_kincaid(words, sentences, syllable_total):
    """Flesch-Kincaid Grade Level (US school grade, lower = easier)."""
    w, s = _denom(words), _denom(sentences)
    return 0.39 * (w / s) + 11.8 * (syllable_total / w) - 15.59


def gunning_fog(words, sentences, complex_words):
    """Gunning Fog index; *complex_words* have 3+ syllables."""
    w, s = _denom(words), _denom(sentences)
    return 0.4 * (w / s + complex_words / w)


def smog(sentences, polysyllables):
    """SMOG grade; *polysyllables* have 3+ syllables."""
    s = _denom(sentences)
    return 1.0430 * (30 * polysyllables / s) ** 0.5 + 3.1291


@dataclass
class Analysis:
    """Result of :func:`analyze`.

    Histograms use integer keys: word lengths 1..``WORD_HIST_MAX``
    (bin ``WORD_HIST_MAX`` counts words of that length or more);
    sentence lengths bucket by ``SENT_HIST_BUCKET`` ranges, keyed by
    the low end of the range (1 = 1-5 words, 6 = 6-10, ...).
    """

    sentences: int
    paragraphs: int
    words: int
    unique_words: int
    syllable_total: int
    unique_ratio: float
    avg_sentence_length: float
    avg_word_length: float
    avg_syllables_per_word: float
    word_length_hist: dict
    sentence_length_hist: dict
    flesch: float
    flesch_kincaid: float
    gunning_fog: float
    smog: float

    def to_dict(self):
        """Return the analysis as a plain JSON-serializable dict."""
        return {
            "sentences": self.sentences,
            "paragraphs": self.paragraphs,
            "words": self.words,
            "unique_words": self.unique_words,
            "syllable_total": self.syllable_total,
            "unique_ratio": self.unique_ratio,
            "avg_sentence_length": self.avg_sentence_length,
            "avg_word_length": self.avg_word_length,
            "avg_syllables_per_word": self.avg_syllables_per_word,
            "word_length_hist": self.word_length_hist,
            "sentence_length_hist": self.sentence_length_hist,
            "flesch": self.flesch,
            "flesch_kincaid": self.flesch_kincaid,
            "gunning_fog": self.gunning_fog,
            "smog": self.smog,
        }


def _word_length_hist(word_lengths):
    hist = {n: 0 for n in range(1, WORD_HIST_MAX + 1)}
    for length in word_lengths:
        hist[min(length, WORD_HIST_MAX)] += 1
    return hist


def _sentence_length_hist(sentence_lengths):
    if not sentence_lengths:
        return {}
    max_start = 1 + ((max(sentence_lengths) - 1) // SENT_HIST_BUCKET) * SENT_HIST_BUCKET
    hist = {start: 0 for start in range(1, max_start + 1, SENT_HIST_BUCKET)}
    for length in sentence_lengths:
        start = 1 + ((length - 1) // SENT_HIST_BUCKET) * SENT_HIST_BUCKET
        hist[start] += 1
    return hist


def _paragraphs(text):
    return sum(1 for block in _BLANK_LINE.split(text) if block.strip())


def analyze(text):
    """Compute every statistic for *text*.

    Empty or punctuation-only input is well-defined: all counts are 0
    (or empty dicts), averages are 0.0, and the readability scores stay
    finite because their denominators are floored at 1.
    """
    text = (text or "").replace("\r\n", "\n").replace("\r", "\n")

    sentence_lengths = []
    all_words = []
    for sentence in tokenize_sentences(text):
        words = tokenize_words(sentence)
        if not words:
            continue
        sentence_lengths.append(len(words))
        all_words.extend(words)

    words_count = len(all_words)
    sentences_count = len(sentence_lengths)
    syllable_total = sum(syllables(w) for w in all_words)
    unique_words = len(set(all_words))
    complex_words = sum(1 for w in all_words if syllables(w) >= 3)

    return Analysis(
        sentences=sentences_count,
        paragraphs=_paragraphs(text),
        words=words_count,
        unique_words=unique_words,
        syllable_total=syllable_total,
        unique_ratio=unique_words / words_count if words_count else 0.0,
        avg_sentence_length=words_count / sentences_count if sentences_count else 0.0,
        avg_word_length=sum(len(w) for w in all_words) / words_count if words_count else 0.0,
        avg_syllables_per_word=syllable_total / words_count if words_count else 0.0,
        word_length_hist=_word_length_hist(len(w) for w in all_words),
        sentence_length_hist=_sentence_length_hist(sentence_lengths),
        flesch=flesch(words_count, sentences_count, syllable_total),
        flesch_kincaid=flesch_kincaid(words_count, sentences_count, syllable_total),
        gunning_fog=gunning_fog(words_count, sentences_count, complex_words),
        smog=smog(sentences_count, complex_words),
    )