from __future__ import annotations

import json
import math
import os
import re
import shutil
import subprocess
import threading
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from app.config import settings
from app.errors import ProcessingError
from app.utils.logging import get_logger
from app.utils.text import clean_text

logger = get_logger(__name__)

_whisper_model = None
_whisper_lock = threading.Lock()


@lru_cache(maxsize=4)
def _resolve_binary(configured: str, name: str) -> str | None:
    candidate = Path(configured)
    if candidate.is_file():
        return str(candidate)
    direct = shutil.which(configured) or shutil.which(name)
    if direct:
        return direct
    # WinGet installs are not always on the inherited PATH (common on Windows dev machines).
    local_appdata = os.getenv("LOCALAPPDATA")
    if local_appdata:
        packages = Path(local_appdata) / "Microsoft" / "WinGet" / "Packages"
        if packages.exists():
            matches = list(packages.glob(f"**/bin/{name}.exe"))
            if matches:
                return str(matches[0])
    for base in (Path("C:/ffmpeg/bin"), Path("/usr/local/bin"), Path("/usr/bin")):
        for suffix in (f"{name}.exe", name):
            if (base / suffix).is_file():
                return str(base / suffix)
    return None


@dataclass
class TranscriptSegment:
    start: float
    end: float
    text: str
    confidence: float | None = None


@dataclass
class TranscriptResult:
    text: str
    segments: list[TranscriptSegment] = field(default_factory=list)
    language: str | None = None
    duration: float | None = None
    model: str = "whisper"
    confidence: float | None = None


def ffmpeg_binary() -> str | None:
    return _resolve_binary(settings.ffmpeg_path, "ffmpeg")


def ffprobe_binary() -> str | None:
    return _resolve_binary(settings.ffprobe_path, "ffprobe")


def ffmpeg_available() -> bool:
    return bool(ffmpeg_binary())


def ensure_ffmpeg_on_path() -> None:
    """Whisper shells out to `ffmpeg`; make the resolved binary visible to it."""
    binary = ffmpeg_binary()
    if not binary:
        return
    directory = str(Path(binary).parent)
    current = os.environ.get("PATH", "")
    if directory.lower() not in current.lower():
        os.environ["PATH"] = directory + os.pathsep + current


def probe_media(path: Path) -> dict:
    ffprobe = ffprobe_binary()
    if ffprobe:
        try:
            result = subprocess.run(
                [
                    ffprobe,
                    "-v",
                    "error",
                    "-print_format",
                    "json",
                    "-show_format",
                    "-show_streams",
                    str(path),
                ],
                capture_output=True,
                text=True,
                timeout=60,
                check=True,
            )
            data = json.loads(result.stdout or "{}")
            streams = data.get("streams", [])
            fmt = data.get("format", {})
            video = next((s for s in streams if s.get("codec_type") == "video"), None)
            audio = next((s for s in streams if s.get("codec_type") == "audio"), None)
            duration = float(fmt.get("duration") or (video or audio or {}).get("duration") or 0) or None
            return {
                "duration": duration,
                "format": fmt.get("format_name"),
                "bitRate": int(fmt["bit_rate"]) if str(fmt.get("bit_rate", "")).isdigit() else None,
                "width": video.get("width") if video else None,
                "height": video.get("height") if video else None,
                "fps": _parse_fps(video.get("avg_frame_rate")) if video else None,
                "videoCodec": video.get("codec_name") if video else None,
                "audioCodec": audio.get("codec_name") if audio else None,
                "sampleRate": audio.get("sample_rate") if audio else None,
            }
        except (subprocess.SubprocessError, ValueError, OSError) as exc:
            logger.warning("ffprobe failed for %s: %s", path.name, exc)

    # Fallback: parse the ffmpeg banner (ffprobe is not bundled with some installs)
    ffmpeg = ffmpeg_binary()
    if ffmpeg:
        try:
            result = subprocess.run([ffmpeg, "-i", str(path)], capture_output=True, text=True, timeout=60)
            banner = result.stderr
            match = re.search(r"Duration: (\d+):(\d+):(\d+(?:\.\d+)?)", banner)
            duration = None
            if match:
                duration = int(match.group(1)) * 3600 + int(match.group(2)) * 60 + float(match.group(3))
            resolution = re.search(r", (\d{2,5})x(\d{2,5})[, ]", banner)
            return {
                "duration": duration,
                "width": int(resolution.group(1)) if resolution else None,
                "height": int(resolution.group(2)) if resolution else None,
            }
        except (subprocess.SubprocessError, OSError):
            pass
    return {"duration": None}


def _parse_fps(value: str | None) -> float | None:
    if not value or value == "0/0":
        return None
    try:
        numerator, denominator = value.split("/")
        return round(float(numerator) / float(denominator), 3)
    except (ValueError, ZeroDivisionError):
        return None


def convert_to_wav(source: Path, destination: Path) -> Path:
    ffmpeg = ffmpeg_binary()
    if not ffmpeg:
        raise ProcessingError(
            "FFmpeg is not installed. Install FFmpeg or set FFMPEG_PATH to process audio and video."
        )
    destination.parent.mkdir(parents=True, exist_ok=True)
    command = [
        ffmpeg,
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(source),
        "-vn",
        "-ac",
        "1",
        "-ar",
        "16000",
        "-c:a",
        "pcm_s16le",
        str(destination),
    ]
    try:
        subprocess.run(command, capture_output=True, text=True, timeout=600, check=True)
    except subprocess.CalledProcessError as exc:
        raise ProcessingError("Audio could not be decoded by FFmpeg.", {"stderr": exc.stderr[-500:]}) from exc
    if not destination.exists() or destination.stat().st_size == 0:
        raise ProcessingError("FFmpeg produced no audio stream.")
    return destination


def _load_whisper():
    global _whisper_model
    if _whisper_model is None:
        try:
            import whisper  # type: ignore
        except ImportError as exc:
            raise ProcessingError(
                "Whisper is not installed. Install openai-whisper from requirements.txt to transcribe audio."
            ) from exc
        model_name = settings.whisper_model
        logger.info("Loading Whisper model '%s' (first load may download weights)", model_name)
        try:
            _whisper_model = whisper.load_model(model_name, device="cpu")
        except Exception as exc:  # network / memory errors
            raise ProcessingError(
                f"Whisper model '{model_name}' could not be loaded.",
                {"error": str(exc)},
            ) from exc
    return _whisper_model


def transcribe_audio(source: Path, work_dir: Path) -> TranscriptResult:
    if not ffmpeg_available():
        raise ProcessingError("FFmpeg is required to prepare audio for transcription.")
    if source.suffix.lower() == ".wav":
        wav_path = source
    else:
        wav_path = convert_to_wav(source, work_dir / "audio_16k.wav")
    ensure_ffmpeg_on_path()
    with _whisper_lock:
        model = _load_whisper()
        try:
            result = model.transcribe(
                str(wav_path),
                language=settings.whisper_language or None,
                fp16=False,
                verbose=False,
            )
        except Exception as exc:
            raise ProcessingError("Whisper failed to transcribe this recording.", {"error": str(exc)}) from exc

    segments = [
        TranscriptSegment(
            start=float(segment.get("start", 0)),
            end=float(segment.get("end", 0)),
            text=clean_text(str(segment.get("text", ""))),
            confidence=_segment_confidence(segment.get("avg_logprob")),
        )
        for segment in result.get("segments", [])
        if str(segment.get("text", "")).strip()
    ]
    text = clean_text(" ".join(segment.text for segment in segments)) or clean_text(str(result.get("text", "")))
    confidence_values = [segment.confidence for segment in segments if segment.confidence is not None]
    return TranscriptResult(
        text=text,
        segments=segments,
        language=result.get("language"),
        duration=segments[-1].end if segments else None,
        model=f"whisper-{settings.whisper_model}",
        confidence=round(sum(confidence_values) / len(confidence_values), 4) if confidence_values else None,
    )


def _segment_confidence(avg_logprob: float | None) -> float | None:
    if avg_logprob is None:
        return None
    try:
        return round(max(0.0, min(1.0, math.exp(float(avg_logprob)))), 4)
    except (ValueError, OverflowError):
        return None


def audio_available() -> bool:
    import importlib.util

    return ffmpeg_available() and importlib.util.find_spec("whisper") is not None
