# textstats

Plain-English text-analysis CLI: sentence/word/paragraph counts, average
sentence and word length, word-length and sentence-length histograms,
unique-vocabulary ratio, and the classic readability scores (**Flesch
Reading Ease**, **Flesch–Kincaid Grade Level**, **Gunning Fog**, **SMOG**),
with AP-style rough syllable counting.

Deterministic, offline, Python standard library only — no network, no model
downloads, no dependencies.

## Features

- Sentence, word and paragraph counts
- Average sentence length, word length and syllables per word
- Word-length histogram (bins 1–12, where `12+` means length ≥ 12)
- Sentence-length histogram (5-word buckets: 1–5, 6–10, …)
- Unique-vocabulary ratio (`unique / total`)
- Four classic readability scores
- AP-style rough vowel-group syllable counter
- `--json` machine output, `--no-histograms`, `--version`, `--help`
- Reads a `FILE` or standard input; `-` means stdin
- Empty input is well-defined: all zeros, finite scores, exit 0

## Install

```sh
pip install -e .
```

Requires Python ≥ 3.9. Installs the `textstats` console script.

## Usage

```sh
textstats [FILE] [--json] [--no-histograms] [--version] [--help]
```

With no `FILE` (or `FILE` = `-`), text comes from stdin.

### Verified example

Running `textstats examples/sample.txt` produces exactly:

```
textstats 1.0.0
Source: examples/sample.txt

Counts
  paragraphs : 2
  sentences  : 3
  words      : 37
  unique     : 28
  unique ratio: 0.76

Averages
  words per sentence : 12.33
  letters per word   : 4.00
  syllables per word : 1.22

Word length histogram (1..12, 12+ means length >= 12)
  1  : 0
  2  : 3
  3  : 13
  4  : 7
  5  : 9
  6  : 5
  7  : 0
  8  : 0
  9  : 0
  10 : 0
  11 : 0
  12+: 0
Sentence length histogram (buckets of 5 words)
  1-5: 0
  6-10: 1
  11-15: 1
  16-20: 1

Readability
  Flesch Reading Ease : 91.42
  Flesch-Kincaid Grade: 3.57
  Gunning Fog         : 4.94
  SMOG                : 6.43
```

### JSON output (floats rounded to 2 decimals)

```sh
printf 'Hello, world! This is only a test.' | textstats --json
```

```json
{
  "sentences": 2,
  "paragraphs": 1,
  "words": 7,
  "unique_words": 7,
  "syllable_total": 9,
  "unique_ratio": 1.0,
  "avg_sentence_length": 3.5,
  "avg_word_length": 3.57,
  "avg_syllables_per_word": 1.29,
  "word_length_hist": {
    "1": 1,
    "2": 1,
    "3": 0,
    "4": 3,
    "5": 2,
    "6": 0,
    "7": 0,
    "8": 0,
    "9": 0,
    "10": 0,
    "11": 0,
    "12": 0
  },
  "sentence_length_hist": {
    "1": 2
  },
  "flesch": 94.51,
  "flesch_kincaid": 0.95,
  "gunning_fog": 1.4,
  "smog": 3.13
}
```

### Errors

A missing/unreadable file exits with code 2 and a message on stderr:

```sh
$ textstats /does/not/exist.txt
textstats: error: cannot read '/does/not/exist.txt': No such file or directory
$ echo $?
2
```

## Flags

| Flag | Meaning |
| --- | --- |
| `FILE` | text file to analyze (default: stdin; `-` also means stdin) |
| `--json` | print the full stats dict as JSON, floats rounded to 2 decimals |
| `--no-histograms` | omit the histogram sections from the readable block |
| `--version` | print `textstats 1.0.0` and exit |
| `--help` | show usage and exit |

## Methodology — honest approximations

The metrics are deliberately simple, reproducible and **approximate**:

- **Sentence splitter.** A sentence ends at `.`, `!` or `?` that is followed
  by whitespace (or the end of the input). Abbreviation periods such as the
  one in `Mr. Jones` therefore *do* split — `Mr` counts as a one-word
  sentence. A proper abbreviation-aware splitter (e.g. via a dictionary of
  known abbreviations) is out of scope.
- **Words.** A word is a run of letters, digits and apostrophes; everything
  else (punctuation, whitespace, en/em dashes) separates words. Words are
  lowercased for counting, and stray edge apostrophes (`'tis`, `dogs'`) are
  dropped.
- **Syllables.** AP-style vowel-group counting: count runs of vowel letters
  (`a e i o u y`), subtract a silent final `e` when it follows a consonant
  and the earlier vowel run is a single vowel letter (so `maybe` = 2 by the
  same rule that makes `love` = 1). This over/under-counts on purpose —
  e.g. `lovely` scores 3, not 2. There is no dictionary lookup.
- **Readability.** Scores use the standard formulas with `w` words,
  `s` sentences, `sy` syllables and `c` = words of 3+ syllables:
  - Flesch Reading Ease = `206.835 − 1.015·w/s − 84.6·sy/w`
  - Flesch–Kincaid Grade = `0.39·w/s + 11.8·sy/w − 15.59`
  - Gunning Fog = `0.4·(w/s + c/w)`
  - SMOG = `1.0430·√(30·c/s) + 3.1291`
- **Empty input.** Counts are 0, averages are 0.0, and readability
  denominators are floored at 1, so empty text produces finite, defined
  scores (`flesch≈205.82`, `flesch_kincaid≈−15.2`, `gunning_fog≈0.4`,
  `smog≈3.13`) — never `NaN` or a crash, and the process exits 0.

`word_length_hist` uses integer buckets 1…12 where **12 counts words of
length 12 or more**; `sentence_length_hist` buckets sentences into ranges
of 5 words keyed by the range start (`1` = 1–5 words, `6` = 6–10, …).

## Library API

```python
from textstats import analyze, syllables, tokenize_sentences

sentences = tokenize_sentences("Mr. Smith left. The dog ran!")
print(sentences)          # ['Mr', 'Smith left', 'The dog ran']
print(syllables("maybe")) # 2

result = analyze("The quick brown fox jumps over the lazy dog.")
print(result.words, result.unique_ratio, result.flesch)
print(result.to_dict())   # JSON-serializable dict
```

## Development

```sh
python3 -m unittest discover -s tests -v
```

The test suite pins every implementation detail with concrete, hand-computed
values: an exact tokenization of a tricky punctuation paragraph, a syllable
table, the four readability scores on a fixed 4-sentence/29-word corpus
(hand-checked: 29 words, 4 sentences, 39 syllables, 2 complex words), exact
histograms, unique-ratio, defined empty-text behavior, and end-to-end CLI
checks (block sections, JSON numbers, stdin, missing-file exit code 2).

## License

MIT © 2026 Conedope. See [LICENSE](LICENSE).