import os
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import cards  # noqa: E402
import render  # noqa: E402

UPDATED = datetime(2026, 1, 1, tzinfo=timezone.utc)


class TopLanguagesTest(unittest.TestCase):
    def test_sorted_limited_and_normalised(self):
        items = render.top_languages({"A": 10, "B": 30, "C": 60, "D": 0}, {}, count=2)
        self.assertEqual([n for n, _, _ in items], ["C", "B"])
        self.assertAlmostEqual(sum(p for _, p, _ in items), 100)

    def test_hide_is_case_insensitive(self):
        items = render.top_languages({"HTML": 99, "Python": 1}, {}, hide=["html "])
        self.assertEqual([n for n, _, _ in items], ["Python"])

    def test_missing_color_falls_back(self):
        items = render.top_languages({"X": 1}, {"X": None})
        self.assertEqual(items[0][2], "#858585")

    def test_empty(self):
        self.assertEqual(render.top_languages({}, {}), [])


class RenderTest(unittest.TestCase):
    def test_every_theme_renders_valid_xml(self):
        items = render.top_languages(*cards.DEMO_LANGS)
        for name, theme in render.THEMES.items():
            with self.subTest(theme=name):
                ET.fromstring(render.render_stats(cards.DEMO_STATS, theme, UPDATED))
                ET.fromstring(render.render_languages(items, theme))
                ET.fromstring(render.render_languages([], theme))

    def test_names_are_escaped(self):
        stats = dict(cards.DEMO_STATS, name="<script>&")
        svg = render.render_stats(stats, render.THEMES["tokyonight"], UPDATED)
        self.assertNotIn("<script>", svg)
        ET.fromstring(svg)

    def test_numbers_are_formatted(self):
        svg = render.render_stats(cards.DEMO_STATS, render.THEMES["tokyonight"], UPDATED)
        self.assertIn("2,481", svg)
        self.assertIn("updated 2026-01-01", svg)


class CliTest(unittest.TestCase):
    def test_demo_writes_both_cards(self):
        with tempfile.TemporaryDirectory() as out:
            self.assertEqual(cards.main(["--demo", "--output-dir", out]), 0)
            self.assertEqual(sorted(os.listdir(out)), ["languages.svg", "stats.svg"])

    def test_single_card(self):
        with tempfile.TemporaryDirectory() as out:
            cards.main(["--demo", "--cards", "languages", "--output-dir", out])
            self.assertEqual(os.listdir(out), ["languages.svg"])

    def test_missing_token_fails(self):
        old = os.environ.pop("PSC_TOKEN", None)
        try:
            self.assertEqual(cards.main(["--output-dir", "unused"]), 1)
        finally:
            if old is not None:
                os.environ["PSC_TOKEN"] = old

    def test_bad_theme_rejected(self):
        with self.assertRaises(SystemExit):
            cards.parse_args(["--theme", "nope"])


if __name__ == "__main__":
    unittest.main()
