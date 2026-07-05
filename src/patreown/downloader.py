from pathlib import Path
from urllib.parse import unquote, urlparse

import requests


DEFAULT_DOWNLOAD_DIR = Path("downloads")


def filename_from_url(url: str) -> str:
    path = urlparse(url).path
    filename = Path(unquote(path)).name

    if not filename:
        return "downloaded-video"

    return filename


def download_file(url: str, output_dir: Path = DEFAULT_DOWNLOAD_DIR) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)

    filename = filename_from_url(url)
    output_path = output_dir / filename

    response = requests.get(url, stream=True, timeout=30)
    response.raise_for_status()

    with output_path.open("wb") as file:
        for chunk in response.iter_content(chunk_size=1024 * 1024):
            if chunk:
                file.write(chunk)

    return output_path