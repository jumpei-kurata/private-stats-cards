"""SVG renderers for the stats and languages cards (standard library only)."""
from html import escape

FONT = '"Segoe UI",Ubuntu,"Helvetica Neue",Sans-Serif'

THEMES = {
    "tokyonight": {
        "bg": "#1a1b27", "border": "#1a1b27", "title": "#70a5fd",
        "text": "#38bdae", "value": "#38bdae", "icon": "#bf91f3", "muted": "#a9b1d6",
    },
    "github-dark": {
        "bg": "#0d1117", "border": "#30363d", "title": "#58a6ff",
        "text": "#c9d1d9", "value": "#f0f6fc", "icon": "#8b949e", "muted": "#8b949e",
    },
    "github-light": {
        "bg": "#ffffff", "border": "#d0d7de", "title": "#0969da",
        "text": "#1f2328", "value": "#1f2328", "icon": "#656d76", "muted": "#656d76",
    },
    "dracula": {
        "bg": "#282a36", "border": "#44475a", "title": "#ff79c6",
        "text": "#f8f8f2", "value": "#f8f8f2", "icon": "#8be9fd", "muted": "#6272a4",
    },
}

STAT_LABELS = {
    "commits": "Total Commits (last year)",
    "prs": "Pull Requests (all time)",
    "contributions": "Contributions (last year)",
    "reviews": "PRs Reviewed (all time)",
    "issues": "Issues (all time)",
    "repos": "Repositories",
    "repos_contributed": "Repos Committed To (last year)",
}
DEFAULT_ROWS = ["commits", "prs", "contributions", "issues", "repos", "repos_contributed"]


def _frame(width, height, label, theme, style):
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" aria-labelledby="title">',
        f"<title id=\"title\">{escape(label)}</title>",
        f"<style>{style}</style>",
        f'<rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="4.5" '
        f'fill="{theme["bg"]}" stroke="{theme["border"]}"/>',
    ]


def render_stats(stats, theme, updated, rows=None):
    """stats: dict from github.fetch_stats; updated: datetime for the footer;
    rows: keys of STAT_LABELS in display order (default DEFAULT_ROWS)."""
    rows = rows or DEFAULT_ROWS
    width, pad = 467, 25
    height = 75 + len(rows) * 26 + 10
    title = f"{stats['name']}'s GitHub Stats"
    style = (
        f".t{{font:600 18px {FONT};fill:{theme['title']}}}"
        f".k{{font:600 14px {FONT};fill:{theme['text']}}}"
        f".v{{font:700 14px {FONT};fill:{theme['value']}}}"
        f".n{{font:400 10px {FONT};fill:{theme['muted']}}}"
    )
    parts = _frame(width, height, title, theme, style)
    parts.append(f'<text x="{pad}" y="35" class="t">{escape(title)}</text>')
    for i, key in enumerate(rows):
        label = STAT_LABELS[key]
        y = 72 + i * 26
        parts.append(f'<circle cx="{pad + 6}" cy="{y - 5}" r="4" fill="{theme["icon"]}"/>')
        parts.append(f'<text x="{pad + 20}" y="{y}" class="k">{escape(label)}:</text>')
        parts.append(
            f'<text x="{width - pad}" y="{y}" class="v" text-anchor="end">{stats[key]:,}</text>'
        )
    parts.append(
        f'<text x="{pad}" y="{height - 12}" class="n">'
        f"Includes private repositories · updated {updated:%Y-%m-%d}</text>"
    )
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def top_languages(totals, colors, hide=(), count=8):
    """Return [(name, percent, color)] for the `count` largest languages.

    Percentages are relative to the languages shown, like github-readme-stats.
    `hide` is matched case-insensitively.
    """
    hidden = {h.strip().lower() for h in hide if h.strip()}
    kept = [(n, b) for n, b in totals.items() if n.lower() not in hidden and b > 0]
    top = sorted(kept, key=lambda kv: (-kv[1], kv[0]))[: max(count, 1)]
    whole = sum(b for _, b in top) or 1
    return [(n, b / whole * 100, colors.get(n) or "#858585") for n, b in top]


def render_languages(items, theme):
    """items: list from top_languages."""
    width, pad = 350, 25
    rows = max((len(items) + 1) // 2, 1)
    height = 90 + rows * 25
    bar_w = width - pad * 2
    style = (
        f".t{{font:600 18px {FONT};fill:{theme['title']}}}"
        f".l{{font:400 11px {FONT};fill:{theme['text']}}}"
    )
    parts = _frame(width, height, "Most Used Languages", theme, style)
    parts.append(f'<text x="{pad}" y="35" class="t">Most Used Languages</text>')

    if not items:
        parts.append(f'<text x="{pad}" y="85" class="l">No language data yet</text>')
        parts.append("</svg>")
        return "\n".join(parts) + "\n"

    parts.append(
        f'<clipPath id="bar"><rect x="{pad}" y="55" width="{bar_w}" height="8" rx="5"/></clipPath>'
    )
    parts.append('<g clip-path="url(#bar)">')
    x = pad
    for _, pct, color in items:
        w = bar_w * pct / 100
        parts.append(
            f'<rect x="{x:.2f}" y="55" width="{w + 0.5:.2f}" height="8" fill="{escape(color)}"/>'
        )
        x += w
    parts.append("</g>")

    for i, (name, pct, color) in enumerate(items):
        cx = pad + (i % 2) * 150
        cy = 85 + (i // 2) * 25
        parts.append(f'<circle cx="{cx + 5}" cy="{cy - 4}" r="5" fill="{escape(color)}"/>')
        parts.append(f'<text x="{cx + 15}" y="{cy}" class="l">{escape(name)} {pct:.2f}%</text>')
    parts.append("</svg>")
    return "\n".join(parts) + "\n"
