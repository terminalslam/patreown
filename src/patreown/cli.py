from pathlib import Path

import requests
import typer

from patreown import __version__
from patreown.downloader import DEFAULT_DOWNLOAD_DIR, download_file
from patreown.hls import HlsDownloadError, download_hls_stream
from patreown.patreon import (
    extract_patreon_post_metadata,
    extract_patreon_video_sources,
    fetch_patreon_post_html,
    parse_patreon_post_url,
)

app = typer.Typer(
    name="patreown",
    help="Personal offline archive tool for Patreon videos you already have access to.",
    invoke_without_command=True,
)


@app.callback()
def main(
    version: bool = typer.Option(
        False,
        "--version",
        help="Show the installed Patreown version.",
    ),
) -> None:
    if version:
        typer.echo(f"patreown {__version__}")
        raise typer.Exit


@app.command()
def download(
    url: str = typer.Argument(..., help="Direct video URL to download."),
    output_dir: Path = typer.Option(
        DEFAULT_DOWNLOAD_DIR,
        "--output-dir",
        "-o",
        help="Directory where the video should be saved.",
    ),
) -> None:
    """Download a direct video URL."""

    try:
        output_path = download_file(url, output_dir)
    except requests.HTTPError as error:
        raise typer.BadParameter(f"Download failed: {error}") from error
    except requests.RequestException as error:
        raise typer.BadParameter(f"Request failed: {error}") from error

    typer.echo(f"Downloaded to {output_path}")


@app.command()
def inspect(
    url: str = typer.Argument(..., help="URL to inspect."),
    fetch: bool = typer.Option(
        False,
        "--fetch",
        help="Fetch the Patreon post page and show basic response info.",
    ),
    save_html: bool = typer.Option(
        False,
        "--save-html",
        help="Save fetched Patreon HTML to the local debug directory.",
    ),
    cookies: Path | None = typer.Option(
        None,
        "--cookies",
        help="Path to a Netscape-format cookies.txt file for authenticated fetches.",
    ),
    show_source_urls: bool = typer.Option(
        False,
        "--show-source-urls",
        help="Print signed Patreon/Mux media URLs. Hidden by default.",
    ),
) -> None:
    """Inspect a URL and show what Patreown can detect."""

    post = parse_patreon_post_url(url)

    if post is None:
        typer.echo("No supported URL detected.")
        raise typer.Exit(code=1)

    typer.echo("Patreon post detected")
    typer.echo(f"Creator: {post.creator_slug}")
    typer.echo(f"Post slug: {post.post_slug}")
    typer.echo(f"Post ID: {post.post_id}")
    typer.echo(f"Clean URL: {post.clean_url}")

    if not fetch:
        return

    try:
        result = fetch_patreon_post_html(post, cookies_path=cookies)
    except requests.HTTPError as error:
        raise typer.BadParameter(f"Fetch failed: {error}") from error
    except requests.RequestException as error:
        raise typer.BadParameter(f"Request failed: {error}") from error

    typer.echo("")
    typer.echo("Fetch result")
    typer.echo(f"Status: {result.status_code}")
    typer.echo(f"Content type: {result.content_type}")
    typer.echo(f"Size: {len(result.text)} bytes")

    metadata = extract_patreon_post_metadata(result.text)

    if metadata is not None:
        typer.echo("")
        typer.echo("Post metadata")
        typer.echo(f"Title: {metadata.title}")
        typer.echo(f"Type: {metadata.object_type}")
        typer.echo(f"Duration: {metadata.duration}")
        typer.echo(f"Upload date: {metadata.upload_date}")
        typer.echo(f"Accessible for free: {metadata.is_accessible_for_free}")
        typer.echo(
            "Thumbnail: "
            f"{'found' if metadata.thumbnail_url is not None else 'not found'}"
        )

        if show_source_urls and metadata.thumbnail_url is not None:
            typer.echo(f"Thumbnail URL: {metadata.thumbnail_url}")

    video_sources = extract_patreon_video_sources(result.text)

    if video_sources.hls_urls:
        typer.echo("")
        typer.echo("Video sources")
        typer.echo(
            "Main video: "
            f"{'found' if video_sources.main_hls_url is not None else 'not found'}"
        )
        typer.echo(
            "Preview video: "
            f"{'found' if video_sources.preview_hls_url is not None else 'not found'}"
        )
        typer.echo(f"HLS streams: {len(video_sources.hls_urls)}")

        if show_source_urls:
            if video_sources.main_hls_url is not None:
                typer.echo(f"Main URL: {video_sources.main_hls_url}")

            if video_sources.preview_hls_url is not None:
                typer.echo(f"Preview URL: {video_sources.preview_hls_url}")

            typer.echo("")
            typer.echo("All HLS streams")

            for index, hls_url in enumerate(video_sources.hls_urls, start=1):
                typer.echo(f"{index}. {hls_url}")

    if save_html:
        debug_dir = Path("debug")
        debug_dir.mkdir(parents=True, exist_ok=True)

        suffix = "-auth" if cookies is not None else ""
        html_path = debug_dir / f"patreon-{post.post_id}{suffix}.html"
        html_path.write_text(result.text, encoding="utf-8")

        typer.echo(f"Saved HTML to {html_path}")


def _safe_filename(value: str) -> str:
    safe_value = "".join(
        character if character.isalnum() or character in {"-", "_"} else "-"
        for character in value.lower()
    )
    return "-".join(part for part in safe_value.split("-") if part)


@app.command("download-post")
def download_post(
    url: str = typer.Argument(..., help="Patreon post URL to download."),
    cookies: Path = typer.Option(
        ...,
        "--cookies",
        help="Path to a Netscape-format cookies.txt file for authenticated fetches.",
    ),
    output_dir: Path = typer.Option(
        DEFAULT_DOWNLOAD_DIR,
        "--output-dir",
        "-o",
        help="Directory where the video should be saved.",
    ),
) -> None:
    """Download the main video from a Patreon post."""

    post = parse_patreon_post_url(url)

    if post is None:
        typer.echo("No supported Patreon post URL detected.")
        raise typer.Exit(code=1)

    typer.echo("Patreon post detected")
    typer.echo(f"Creator: {post.creator_slug}")
    typer.echo(f"Post ID: {post.post_id}")

    try:
        result = fetch_patreon_post_html(post, cookies_path=cookies)
    except requests.HTTPError as error:
        raise typer.BadParameter(f"Fetch failed: {error}") from error
    except requests.RequestException as error:
        raise typer.BadParameter(f"Request failed: {error}") from error

    metadata = extract_patreon_post_metadata(result.text)
    video_sources = extract_patreon_video_sources(result.text)

    if video_sources.main_hls_url is None:
        raise typer.BadParameter("No main Patreon video source found.")

    title = metadata.title if metadata is not None and metadata.title else post.post_slug
    filename = f"{_safe_filename(title)}-{post.post_id}.mp4"
    output_path = output_dir / post.creator_slug / filename

    typer.echo("Main video source found")
    typer.echo(f"Downloading to {output_path}")

    try:
        downloaded_path = download_hls_stream(
            video_sources.main_hls_url,
            output_path,
            referer=post.clean_url,
        )
    except HlsDownloadError as error:
        raise typer.BadParameter(str(error)) from error

    typer.echo(f"Downloaded to {downloaded_path}")