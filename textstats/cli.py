"""Command-line interface for textstats."""

import argparse
import json
import sys

from . import __version__
from .analyze import SENT_HIST_BUCKET, WORD_HIST_MAX, analyze

FLOAT_KEYS = (
    "unique_ratio",
    "avg_sentence_length",
    "avg_word_length",
    "avg_syllables_per_word",
    "flesch",
    "flesch_kincaid",
    "gunning_fog",
    "smog",
)


def build_parser():
    parser = argparse.ArgumentParser(
        prog="textstats",
        description="Plain-English text statistics and readability scores.",
        epilog="Reads FILE, or standard input when FILE is omitted. "
               "Empty input is not an error (all zeros, defined scores).",
    )
    parser.add_argument("file", nargs="?", default=None, help="text file to analyze (default: stdin)")
    parser.add_argument("--json", action="store_true", help="output the full stats as JSON")
    parser.add_argument("--no-histograms", action="store_true", help="omit histogram sections")
    parser.add_argument("--version", action="version", version="%(prog)s " + __version__)
    return parser


def _rounded_dict(analysis):
    data = analysis.to_dict()
    for key in FLOAT_KEYS:
        data[key] = round(data[key], 2)
    return data


def format_block(analysis, source, histograms=True):
    out = []
    out.append("textstats %s" % __version__)
    out.append("Source: %s" % source)
    out.append("")
    out.append("Counts")
    out.append("  paragraphs : %d" % analysis.paragraphs)
    out.append("  sentences  : %d" % analysis.sentences)
    out.append("  words      : %d" % analysis.words)
    out.append("  unique     : %d" % analysis.unique_words)
    out.append("  unique ratio: %.2f" % analysis.unique_ratio)
    out.append("")
    out.append("Averages")
    out.append("  words per sentence : %.2f" % analysis.avg_sentence_length)
    out.append("  letters per word   : %.2f" % analysis.avg_word_length)
    out.append("  syllables per word : %.2f" % analysis.avg_syllables_per_word)
    out.append("")
    if histograms:
        word_hist = analysis.word_length_hist
        sent_hist = analysis.sentence_length_hist
        out.append("Word length histogram (1..%d, %d+ means length >= %d)" % (WORD_HIST_MAX, WORD_HIST_MAX, WORD_HIST_MAX))
        for key in range(1, WORD_HIST_MAX + 1):
            label = "%d" % key if key < WORD_HIST_MAX else "%d+" % key
            out.append("  %-3s: %d" % (label, word_hist[key]))
        out.append("Sentence length histogram (buckets of %d words)" % SENT_HIST_BUCKET)
        if sent_hist:
            for key in sorted(sent_hist):
                out.append("  %d-%d: %d" % (key, key + SENT_HIST_BUCKET - 1, sent_hist[key]))
        else:
            out.append("  (none)")
        out.append("")
    out.append("Readability")
    out.append("  Flesch Reading Ease : %.2f" % analysis.flesch)
    out.append("  Flesch-Kincaid Grade: %.2f" % analysis.flesch_kincaid)
    out.append("  Gunning Fog         : %.2f" % analysis.gunning_fog)
    out.append("  SMOG                : %.2f" % analysis.smog)
    return "\n".join(out) + "\n"


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.file is None or args.file == "-":
        source = "<stdin>"
        text = sys.stdin.read()
    else:
        source = args.file
        try:
            with open(args.file, "r", encoding="utf-8") as fh:
                text = fh.read()
        except OSError as exc:
            print("textstats: error: cannot read %r: %s" % (args.file, exc.strerror or exc), file=sys.stderr)
            return 2

    analysis = analyze(text)
    if args.json:
        json.dump(_rounded_dict(analysis), sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")
    else:
        sys.stdout.write(format_block(analysis, source, histograms=not args.no_histograms))
    return 0


if __name__ == "__main__":
    sys.exit(main())