import json
from dataclasses import dataclass
from html.parser import HTMLParser
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


@dataclass(frozen=True)
class PatreonPostMetadata:
    title: str | None
    object_type: str | None
    duration: str | None
    upload_date: str | None
    is_accessible_for_free: bool | None
    thumbnail_url: str | None


@dataclass(frozen=True)
class MuxAssetHint:
    playback_id: str
    thumbnail_host: str


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


class JsonLdParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._inside_json_ld = False
        self._current_data: list[str] = []
        self.scripts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "script":
            return

        attrs_dict = dict(attrs)

        if attrs_dict.get("type") == "application/ld+json":
            self._inside_json_ld = True
            self._current_data = []

    def handle_data(self, data: str) -> None:
        if self._inside_json_ld:
            self._current_data.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag != "script" or not self._inside_json_ld:
            return

        self._inside_json_ld = False
        self.scripts.append("".join(self._current_data))
        self._current_data = []


def extract_patreon_post_metadata(html: str) -> PatreonPostMetadata | None:
    parser = JsonLdParser()
    parser.feed(html)

    for script in parser.scripts:
        try:
            data = json.loads(script)
        except json.JSONDecodeError:
            continue

        items = data if isinstance(data, list) else [data]

        for item in items:
            if not isinstance(item, dict):
                continue

            if item.get("@type") != "VideoObject":
                continue

            return PatreonPostMetadata(
                title=item.get("name"),
                object_type=item.get("@type"),
                duration=item.get("duration"),
                upload_date=item.get("uploadDate"),
                is_accessible_for_free=item.get("isAccessibleForFree"),
                thumbnail_url=item.get("thumbnailUrl"),
            )

    return None


def extract_mux_asset_hint(metadata: PatreonPostMetadata) -> MuxAssetHint | None:
    if not metadata.thumbnail_url:
        return None

    parsed = urlparse(metadata.thumbnail_url)

    if parsed.netloc != "image.mux.com":
        return None

    parts = [part for part in parsed.path.split("/") if part]

    if not parts:
        return None

    return MuxAssetHint(
        playback_id=parts[0],
        thumbnail_host=parsed.netloc,
    )