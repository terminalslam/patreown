import shutil
import subprocess
from pathlib import Path


DEFAULT_FFMPEG_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) "
    "Version/17.0 Safari/605.1.15"
)


class HlsDownloadError(Exception):
    pass


def download_hls_stream(
    hls_url: str,
    output_path: Path,
    referer: str | None = None,
) -> Path:
    ffmpeg_path = shutil.which("ffmpeg")

    if ffmpeg_path is None:
        raise HlsDownloadError(
            "ffmpeg is not installed or not available on PATH. "
            "Install it with: brew install ffmpeg"
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)

    command = [
        ffmpeg_path,
        "-hide_banner",
        "-loglevel",
        "error",
        "-stats",
        "-n",
        "-user_agent",
        DEFAULT_FFMPEG_USER_AGENT,
    ]

    if referer is not None:
        command.extend(
            [
                "-headers",
                f"Referer: {referer}\r\nOrigin: https://www.patreon.com\r\n",
            ]
        )

    command.extend(
        [
            "-i",
            hls_url,
            "-c",
            "copy",
            str(output_path),
        ]
    )

    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as error:
        raise HlsDownloadError(f"ffmpeg failed with exit code {error.returncode}") from error

    return output_path