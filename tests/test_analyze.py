"""Unit tests for the textstats analysis core (deterministic hand-values)."""

import unittest

from textstats.analyze import (
    analyze,
    flesch,
    flesch_kincaid,
    gunning_fog,
    smog,
    syllables,
    tokenize_sentences,
    tokenize_words,
)

# 4 sentences, 29 words, 39 syllables under our rule.
CORPUS = (
    "The quick brown fox jumps over the lazy dog. "
    "Pack my box with five dozen liquor jugs. "
    "The rainbow is lovely and bright. "
    "How vexingly quick daft zebras jump."
)


class TokenizeSentencesTest(unittest.TestCase):
    def test_simple_splits(self):
        text = "One. Two! Three? Four."
        self.assertEqual(tokenize_sentences(text), ["One", "Two", "Three", "Four"])

    def test_sentence_is_the_text_after_the_mark(self):
        text = "Hello, world! How are you? I'm fine, thanks."
        self.assertEqual(tokenize_sentences(text), ["Hello, world", "How are you", "I'm fine, thanks"])

    def test_tricky_punctuation_paragraph(self):
        text = "Hello, world! How are you? I'm fine, thanks. This is a test\u2014with an em dash and 2 numbers."
        self.assertEqual(
            tokenize_sentences(text),
            [
                "Hello, world",
                "How are you",
                "I'm fine, thanks",
                "This is a test\u2014with an em dash and 2 numbers",
            ],
        )

    def test_abbreviation_period_is_reported_as_boundary(self):
        # Documented simplification: 'Mr.' ends a sentence.
        self.assertEqual(tokenize_sentences("Mr. Jones left."), ["Mr", "Jones left"])

    def test_empty_and_punctuation_only(self):
        self.assertEqual(tokenize_sentences(""), [])
        self.assertEqual(tokenize_sentences("... !!! ???"), [])

    def test_end_of_input_mark(self):
        self.assertEqual(tokenize_sentences("No trailing space."), ["No trailing space"])


class TokenizeWordsTest(unittest.TestCase):
    def test_simple(self):
        self.assertEqual(tokenize_words("The quick brown fox"), ["the", "quick", "brown", "fox"])

    def test_apostrophe_is_kept(self):
        self.assertEqual(tokenize_words("I'm fine"), ["i'm", "fine"])

    def test_edge_apostrophes_stripped(self):
        self.assertEqual(tokenize_words("'tis and dogs'"), ["tis", "and", "dogs"])

    def test_punctuation_and_dashes_split(self):
        self.assertEqual(
            tokenize_words("state-of-the-art: ready!"),
            ["state", "of", "the", "art", "ready"],
        )

    def test_digits_count_as_words(self):
        self.assertEqual(tokenize_words("2 numbers 42"), ["2", "numbers", "42"])

    def test_lowercased(self):
        self.assertEqual(tokenize_words("MiXeD CASE"), ["mixed", "case"])

    def test_empty(self):
        self.assertEqual(tokenize_words(""), [])


class SyllablesTest(unittest.TestCase):
    def test_hand_computed_table(self):
        expected = {
            "hello": 2,
            "world": 1,
            "python": 2,
            "readability": 5,
            "the": 1,
            "maybe": 2,
            "love": 1,
            "cake": 1,
            "bee": 1,
            "book": 1,
            "why": 1,
            "yellow": 2,
            "over": 2,
            "dozen": 2,
            "liquor": 2,
            "lazy": 2,
            "five": 1,
            "rainbow": 2,
            "syllable": 2,
        }
        for word, count in expected.items():
            with self.subTest(word=word):
                self.assertEqual(syllables(word), count)

    def test_rule_documented_approximation(self):
        # 'lovely' is over-counted to 3 by the pure vowel-group rule:
        # the trailing -y contributes a group and silent-e is not applied.
        self.assertEqual(syllables("lovely"), 3)
        self.assertEqual(syllables("vexingly"), 3)

    def test_case_insensitive(self):
        self.assertEqual(syllables("HELLO"), syllables("hello"))
        self.assertEqual(syllables("Python"), 2)

    def test_no_vowels_counts_one(self):
        self.assertEqual(syllables(""), 0)
        self.assertEqual(syllables("shh"), 1)
        self.assertEqual(syllables("myth"), 1)


class ReadabilityScoreTest(unittest.TestCase):
    # Hand-computed on CORPUS: 29 words, 4 sentences, 39 syllables,
    # 2 complex/polysyllabic words (lovely, vexingly).
    def test_flesch(self):
        self.assertAlmostEqual(flesch(29, 4, 39), 85.70383620689658, places=6)

    def test_flesch_kincaid(self):
        self.assertAlmostEqual(flesch_kincaid(29, 4, 39), 3.1064655172413786, places=6)

    def test_gunning_fog(self):
        self.assertAlmostEqual(gunning_fog(29, 4, 2), 2.9275862068965517, places=6)

    def test_smog(self):
        self.assertAlmostEqual(smog(4, 2), 7.168621630094336, places=6)

    def test_zero_counts_stay_finite(self):
        # Empty input must never produce NaN or infinite scores.
        for actual, expected in (
            (flesch(0, 0, 0), 205.82),
            (flesch_kincaid(0, 0, 0), -15.2),
            (gunning_fog(0, 0, 0), 0.4),
            (smog(0, 0), 3.1291),
        ):
            self.assertTrue(isinstance(actual, float) and actual == actual, "got non-finite %r" % actual)
            self.assertAlmostEqual(actual, expected, places=9)


class AnalyzeTest(unittest.TestCase):
    def test_corpus_counts(self):
        a = analyze(CORPUS)
        self.assertEqual(a.sentences, 4)
        self.assertEqual(a.words, 29)
        self.assertEqual(a.paragraphs, 1)
        self.assertEqual(a.syllable_total, 39)
        self.assertEqual(a.unique_words, 26)
        self.assertAlmostEqual(a.unique_ratio, 26 / 29, places=9)

    def test_corpus_averages(self):
        a = analyze(CORPUS)
        self.assertAlmostEqual(a.avg_sentence_length, 7.25, places=9)          # 29 / 4
        self.assertAlmostEqual(a.avg_word_length, 124 / 29, places=9)          # sum(len) / words
        self.assertAlmostEqual(a.avg_syllables_per_word, 39 / 29, places=9)

    def test_corpus_word_length_histogram(self):
        a = analyze(CORPUS)
        expected = {n: 0 for n in range(1, 13)}
        expected[2] = 2
        expected[3] = 8
        expected[4] = 8
        expected[5] = 5
        expected[6] = 4
        expected[7] = 1
        expected[8] = 1
        self.assertEqual(a.word_length_hist, expected)

    def test_corpus_sentence_length_histogram(self):
        a = analyze(CORPUS)
        # Sentence lengths are 9, 8, 6, 6 -> all in the 6-10 bucket.
        self.assertEqual(a.sentence_length_hist, {1: 0, 6: 4})

    def test_corpus_scores(self):
        a = analyze(CORPUS)
        self.assertAlmostEqual(a.flesch, 85.70383620689658, places=6)
        self.assertAlmostEqual(a.flesch_kincaid, 3.1064655172413786, places=6)
        self.assertAlmostEqual(a.gunning_fog, 2.9275862068965517, places=6)
        self.assertAlmostEqual(a.smog, 7.168621630094336, places=6)

    def test_paragraphs(self):
        text = "Paragraph one.\n\n Paragraph two.\n\n\nParagraph three."
        self.assertEqual(analyze(text).paragraphs, 3)

    def test_to_dict(self):
        d = analyze(CORPUS).to_dict()
        self.assertEqual(d["words"], 29)
        self.assertEqual(d["sentences"], 4)
        self.assertEqual(
            sorted(d.keys()),
            sorted(
                [
                    "sentences",
                    "paragraphs",
                    "words",
                    "unique_words",
                    "syllable_total",
                    "unique_ratio",
                    "avg_sentence_length",
                    "avg_word_length",
                    "avg_syllables_per_word",
                    "word_length_hist",
                    "sentence_length_hist",
                    "flesch",
                    "flesch_kincaid",
                    "gunning_fog",
                    "smog",
                ]
            ),
        )

    def test_empty_text_is_defined(self):
        a = analyze("")
        self.assertEqual(a.sentences, 0)
        self.assertEqual(a.paragraphs, 0)
        self.assertEqual(a.words, 0)
        self.assertEqual(a.unique_words, 0)
        self.assertEqual(a.syllable_total, 0)
        self.assertEqual(a.unique_ratio, 0.0)
        self.assertEqual(a.avg_sentence_length, 0.0)
        self.assertEqual(a.avg_word_length, 0.0)
        self.assertEqual(a.avg_syllables_per_word, 0.0)
        self.assertEqual(a.word_length_hist, {n: 0 for n in range(1, 13)})
        self.assertEqual(a.sentence_length_hist, {})
        self.assertAlmostEqual(a.flesch, 205.82, places=9)
        self.assertAlmostEqual(a.flesch_kincaid, -15.2, places=9)
        self.assertAlmostEqual(a.gunning_fog, 0.4, places=9)
        self.assertAlmostEqual(a.smog, 3.1291, places=9)

    def test_punctuation_only_text_is_defined(self):
        a = analyze("??? ... !!!")
        self.assertEqual(a.words, 0)
        self.assertEqual(a.sentences, 0)
        self.assertAlmostEqual(a.flesch, 205.82, places=9)

    def test_long_word_goes_to_top_bin(self):
        a = analyze("Count the characters in antidisestablishmentarianism.")
        self.assertEqual(a.word_length_hist[12], 1)
        self.assertEqual(a.words, 5)


if __name__ == "__main__":
    unittest.main()