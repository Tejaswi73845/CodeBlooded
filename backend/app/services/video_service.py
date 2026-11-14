from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from app.config import settings
from app.errors import ProcessingError
from app.services.audio_service import ffmpeg_available, ffmpeg_binary, probe_media
from app.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class VideoFrame:
    index: int
    path: Path
    timestamp: float


@dataclass
class VideoResult:
    frames: list[VideoFrame] = field(default_factory=list)
    audio_path: Path | None = None
    metadata: dict = field(default_factory=dict)


def extract_video_assets(source: Path, work_dir: Path) -> VideoResult:
    if not ffmpeg_available():
        raise ProcessingError("FFmpeg is required to process video evidence.")
    metadata = probe_media(source)
    duration = metadata.get("duration")
    if not duration:
        raise ProcessingError("Video duration could not be determined.")

    frames_dir = work_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    interval = max(1, settings.video_frame_interval_seconds)
    max_frames = max(1, settings.max_video_frames)
    # First try the configured sampling interval; short clips may produce no
    # frames, so fall back to one frame per second. JPEG encoding also needs
    # full-range YUV on newer ffmpeg builds (hence pix_fmt/strict flags).
    frames: list[VideoFrame] = []
    for filter_expr in (f"fps=1/{interval}", "fps=1"):
        for stale in frames_dir.glob("frame_*.jpg"):
            stale.unlink(missing_ok=True)
        command = [
            ffmpeg_binary(),
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(source),
            "-vf",
            filter_expr,
            "-frames:v",
            str(max_frames),
            "-q:v",
            "3",
            "-pix_fmt",
            "yuvj420p",
            "-strict",
            "unofficial",
            str(frames_dir / "frame_%03d.jpg"),
        ]
        try:
            subprocess.run(command, capture_output=True, text=True, timeout=900, check=True)
        except subprocess.CalledProcessError as exc:
            logger.warning(
                "Frame extraction (%s) failed for %s: %s",
                filter_expr,
                source.name,
                (exc.stderr or "")[-300:],
            )
            continue
        frames = [
            VideoFrame(index=index, path=path, timestamp=round(index * interval, 2))
            for index, path in enumerate(sorted(frames_dir.glob("frame_*.jpg")))
        ]
        if frames:
            break

    if not frames:
        logger.warning("No frames could be extracted from %s; continuing with audio only", source.name)

    audio_path = work_dir / "audio_16k.wav"
    try:
        from app.services.audio_service import convert_to_wav

        convert_to_wav(source, audio_path)
    except ProcessingError:
        logger.info("No audio track extracted from %s", source.name)
        audio_path = None

    metadata.update(
        {
            "frameIntervalSeconds": interval,
            "framesExtracted": len(frames),
            "duration": duration,
            "preview": _preview(metadata),
        }
    )
    return VideoResult(frames=frames, audio_path=audio_path, metadata=metadata)


def _preview(metadata: dict) -> str:
    width, height = metadata.get("width"), metadata.get("height")
    fps = metadata.get("fps")
    parts = [f"{width} × {height}" if width and height else "Video"]
    if fps:
        parts.append(f"{fps:g} fps")
    if metadata.get("videoCodec"):
        parts.append(str(metadata["videoCodec"]).upper())
    return " · ".join(parts)
