from dataclasses import dataclass
from urllib.parse import urlparse, urlunparse

import requests


@dataclass(frozen=True)
class PatreonPostUrl:
    creator_slug: str
    post_slug: str
    post_id: str
    clean_url: str


@dataclass(frozen=True)
class PatreonFetchResult:
    status_code: int
    content_type: str
    text: str


def parse_patreon_post_url(url: str) -> PatreonPostUrl | None:
    parsed = urlparse(url)

    if parsed.netloc not in {"www.patreon.com", "patreon.com"}:
        return None

    parts = [part for part in parsed.path.split("/") if part]

    if len(parts) != 3 or parts[1] != "posts":
        return None

    creator_slug = parts[0]
    post_segment = parts[2]
    post_slug, separator, post_id = post_segment.rpartition("-")

    if not separator or not post_slug or not post_id.isdigit():
        return None

    clean_path = f"/{creator_slug}/posts/{post_slug}-{post_id}"
    clean_url = urlunparse(("https", "www.patreon.com", clean_path, "", "", ""))

    return PatreonPostUrl(
        creator_slug=creator_slug,
        post_slug=post_slug,
        post_id=post_id,
        clean_url=clean_url,
    )


def fetch_patreon_post_html(post: PatreonPostUrl) -> PatreonFetchResult:
    response = requests.get(
        post.clean_url,
        headers={
            "User-Agent": "Patreown/0.1.0",
        },
        timeout=30,
    )
    response.raise_for_status()

    return PatreonFetchResult(
        status_code=response.status_code,
        content_type=response.headers.get("content-type", ""),
        text=response.text,
    )