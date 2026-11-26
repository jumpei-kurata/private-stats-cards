"""Generate GitHub profile cards that count private repositories.

Usage (normally called by action.yml):
    PSC_TOKEN=... python3 src/cards.py --theme tokyonight --output-dir profile
    python3 src/cards.py --demo --output-dir examples/tokyonight   # no token needed

Every option can also come from an environment variable (PSC_THEME, PSC_CARDS,
PSC_HIDE_LANGUAGES, PSC_LANGUAGES_COUNT, PSC_OUTPUT_DIR).
"""
import argparse
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import github  # noqa: E402
import render  # noqa: E402

CARDS = ("stats", "languages")

DEMO_STATS = {
    "name": "Jane Doe", "login": "janedoe", "commits": 2481, "prs": 312,
    "reviews": 157, "issues": 96, "repos": 58, "repos_contributed": 21,
}
DEMO_LANGS = (
    {"TypeScript": 4_200_000, "Python": 3_100_000, "Go": 1_300_000, "Rust": 620_000,
     "Swift": 540_000, "Shell": 210_000, "HCL": 150_000, "SQL": 90_000},
    {"TypeScript": "#3178c6", "Python": "#3572A5", "Go": "#00ADD8", "Rust": "#dea584",
     "Swift": "#F05138", "Shell": "#89e051", "HCL": "#844FBA", "SQL": "#e38c00"},
)
DEMO_DATE = datetime(2026, 1, 1, tzinfo=timezone.utc)


def split_list(value):
    return [v.strip() for v in (value or "").split(",") if v.strip()]


def parse_args(argv):
    env = os.environ.get
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument("--cards", default=env("PSC_CARDS") or "stats,languages")
    p.add_argument("--theme", default=env("PSC_THEME") or "tokyonight")
    p.add_argument("--hide-languages", default=env("PSC_HIDE_LANGUAGES") or "")
    p.add_argument("--languages-count", type=int, default=int(env("PSC_LANGUAGES_COUNT") or 8))
    p.add_argument("--output-dir", default=env("PSC_OUTPUT_DIR") or "profile")
    p.add_argument("--demo", action="store_true", help="render sample data, no token needed")
    args = p.parse_args(argv)

    args.cards = split_list(args.cards)
    unknown = [c for c in args.cards if c not in CARDS]
    if unknown or not args.cards:
        p.error(f"--cards must be a comma-separated subset of {', '.join(CARDS)} (got {unknown or 'nothing'})")
    if args.theme not in render.THEMES:
        p.error(f"unknown theme {args.theme!r}; choose one of {', '.join(render.THEMES)}")
    if not 1 <= args.languages_count <= 20:
        p.error("--languages-count must be between 1 and 20")
    return args


def write(path, svg):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"wrote {path}")


def main(argv=None):
    args = parse_args(argv)
    theme = render.THEMES[args.theme]
    token = os.environ.get("PSC_TOKEN", "").strip()
    if not args.demo and not token:
        print("::error::No token. Pass a fine-grained PAT as `token:` (see README).", file=sys.stderr)
        return 1

    try:
        if "stats" in args.cards:
            if args.demo:
                stats, updated = DEMO_STATS, DEMO_DATE
            else:
                stats, updated = github.fetch_stats(token), datetime.now(timezone.utc)
            write(os.path.join(args.output_dir, "stats.svg"), render.render_stats(stats, theme, updated))
            for label, key in render.STAT_ROWS:
                print(f"  {label}: {stats[key]:,}")

        if "languages" in args.cards:
            if args.demo:
                totals, colors, repo_count = *DEMO_LANGS, 0
            else:
                totals, colors, repo_count = github.fetch_languages(token)
            items = render.top_languages(
                totals, colors, split_list(args.hide_languages), args.languages_count
            )
            write(os.path.join(args.output_dir, "languages.svg"), render.render_languages(items, theme))
            if not args.demo:
                print(f"  repositories scanned: {repo_count}")
            for name, pct, _ in items:
                print(f"  {name}: {pct:.2f}%")
    except github.GitHubError as e:
        print(f"::error::{e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
