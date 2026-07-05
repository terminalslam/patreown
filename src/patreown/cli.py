from pathlib import Path

import requests
import typer

from patreown import __version__
from patreown.downloader import DEFAULT_DOWNLOAD_DIR, download_file

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