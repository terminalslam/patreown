from pathlib import Path

import requests
import typer

from patreown import __version__
from patreown.downloader import DEFAULT_DOWNLOAD_DIR, download_file
from patreown.patreon import (
    extract_patreon_post_metadata,
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

# Inspect Command

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
        typer.echo(f"Thumbnail URL: {metadata.thumbnail_url}")

    if save_html:
        debug_dir = Path("debug")
        debug_dir.mkdir(parents=True, exist_ok=True)

        suffix = "-auth" if cookies is not None else ""
        html_path = debug_dir / f"patreon-{post.post_id}{suffix}.html"
        html_path.write_text(result.text, encoding="utf-8")

        typer.echo(f"Saved HTML to {html_path}")