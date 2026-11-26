"""Tiny GitHub GraphQL client (standard library only).

Only aggregate numbers leave this module. Repository names are never
returned to the caller, so they cannot end up in a rendered card.
"""
import json
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

API = "https://api.github.com/graphql"
USER_AGENT = "private-stats-cards"


class GitHubError(RuntimeError):
    pass


def graphql(token, query, variables=None):
    body = json.dumps({"query": query, "variables": variables or {}}).encode()
    req = urllib.request.Request(
        API,
        data=body,
        headers={
            "Authorization": f"bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": USER_AGENT,
        },
    )
    last_error = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                data = json.loads(r.read())
            break
        except urllib.error.HTTPError as e:
            if e.code == 401:
                raise GitHubError(
                    "GitHub rejected the token (HTTP 401). Check that the secret "
                    "exists, is passed as `token:`, and has not expired."
                ) from None
            last_error = f"HTTP {e.code}"
            if e.code not in (502, 503, 504):
                detail = e.read()[:300].decode("utf-8", "replace")
                raise GitHubError(f"GitHub API returned HTTP {e.code}: {detail}") from None
        except urllib.error.URLError as e:
            last_error = str(e.reason)
        time.sleep(3 * (attempt + 1))
    else:
        raise GitHubError(f"GitHub API did not respond after 3 tries ({last_error}).")

    if data.get("errors"):
        messages = "; ".join(err.get("message", "?") for err in data["errors"])
        raise GitHubError(f"GraphQL error: {messages}")
    return data["data"]


LANGS_QUERY = """
query($cursor: String) {
  viewer {
    repositories(first: 100, after: $cursor, ownerAffiliations: OWNER, isFork: false) {
      pageInfo { hasNextPage endCursor }
      nodes {
        languages(first: 20, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name color } }
        }
      }
    }
  }
}
"""


def fetch_languages(token):
    """Return ({language: bytes}, {language: color}, repo_count) for every
    non-fork repository the token owner owns, public and private."""
    totals, colors, cursor, repo_count = {}, {}, None, 0
    while True:
        page = graphql(token, LANGS_QUERY, {"cursor": cursor})["viewer"]["repositories"]
        for repo in page["nodes"]:
            repo_count += 1
            for edge in repo["languages"]["edges"]:
                name = edge["node"]["name"]
                totals[name] = totals.get(name, 0) + edge["size"]
                colors[name] = edge["node"]["color"] or "#858585"
        if not page["pageInfo"]["hasNextPage"]:
            break
        cursor = page["pageInfo"]["endCursor"]
    return totals, colors, repo_count


VIEWER_QUERY = """
query($from: DateTime!, $to: DateTime!) {
  viewer {
    name
    login
    pullRequests { totalCount }
    issues { totalCount }
    repositories(ownerAffiliations: OWNER) { totalCount }
    contributionsCollection(from: $from, to: $to) {
      totalCommitContributions
      totalPullRequestReviewContributions
      restrictedContributionsCount
      totalRepositoriesWithContributedCommits
    }
  }
}
"""

SEARCH_QUERY = """
query($prq: String!, $isq: String!, $rvq: String!) {
  prs: search(query: $prq, type: ISSUE) { issueCount }
  issues: search(query: $isq, type: ISSUE) { issueCount }
  reviews: search(query: $rvq, type: ISSUE) { issueCount }
}
"""


def fetch_stats(token, now=None):
    """Return a dict of headline numbers for the token owner."""
    now = now or datetime.now(timezone.utc)
    year_ago = now - timedelta(days=365)
    v = graphql(token, VIEWER_QUERY, {"from": year_ago.isoformat(), "to": now.isoformat()})["viewer"]
    login = v["login"]

    # With fine-grained tokens, viewer.pullRequests / viewer.issues can come
    # back far too low. Search counts everything the token can see, so take
    # whichever number is larger.
    s = graphql(token, SEARCH_QUERY, {
        "prq": f"author:{login} is:pr",
        "isq": f"author:{login} is:issue",
        "rvq": f"reviewed-by:{login} is:pr -author:{login}",
    })

    cc = v["contributionsCollection"]
    return {
        "name": v["name"] or login,
        "login": login,
        "commits": cc["totalCommitContributions"] + cc["restrictedContributionsCount"],
        "prs": max(v["pullRequests"]["totalCount"], s["prs"]["issueCount"]),
        "reviews": max(cc["totalPullRequestReviewContributions"], s["reviews"]["issueCount"]),
        "issues": max(v["issues"]["totalCount"], s["issues"]["issueCount"]),
        "repos": v["repositories"]["totalCount"],
        "repos_contributed": cc["totalRepositoriesWithContributedCommits"],
    }
