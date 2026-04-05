from mutagen import File as MutagenFile
from pathlib import Path
from typing import Optional, Dict, Any


def detect_codec(file_path: Path) -> Optional[Dict[str, Any]]:
    """
    Detect audio codec and metadata from a file.

    Args:
        file_path: Path to the audio file

    Returns:
        Dict with codec info or None if detection fails
    """
    try:
        audio = MutagenFile(str(file_path))
        if not audio:
            return None

        info = {
            "codec": type(audio).__name__.lower(),
            "bitrate": getattr(audio.info, "bitrate", None),
            "sample_rate": getattr(audio.info, "sample_rate", None),
            "duration": getattr(audio.info, "length", None),
            "channels": getattr(audio.info, "channels", None),
        }

        if hasattr(audio, "format"):
            info["format"] = audio.format

        return info
    except Exception:
        return None


def get_codec_name(file_path: Path) -> str:
    """
    Get simple codec name from file.

    Returns:
        Codec string like 'mp3', 'ogg', 'flac', 'aac', 'unknown'
    """
    info = detect_codec(file_path)
    if not info:
        return "unknown"

    codec = info.get("codec", "")

    if "mp3" in codec:
        return "mp3"
    elif "ogg" in codec:
        return "ogg"
    elif "flac" in codec:
        return "flac"
    elif "aac" in codec:
        return "aac"
    elif "wav" in codec:
        return "wav"
    elif "opus" in codec:
        return "opus"
    else:
        return codec
