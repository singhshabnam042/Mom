"""
audio_extractor.py
==================
FFmpeg ki madad se video files se audio extract karta hai.
Supports: MP4, MKV, AVI, MOV, WEBM → WAV/MP3
"""

import os
import subprocess
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Supported input formats
SUPPORTED_VIDEO_FORMATS = {".mp4", ".mkv", ".avi", ".mov", ".webm"}
SUPPORTED_AUDIO_FORMATS = {".mp3", ".wav", ".m4a", ".ogg", ".flac"}
ALL_SUPPORTED_FORMATS = SUPPORTED_VIDEO_FORMATS | SUPPORTED_AUDIO_FORMATS


class AudioExtractor:
    """
    Video ya audio file se clean WAV audio extract karta hai.

    Usage::

        extractor = AudioExtractor()
        audio_path = extractor.extract("meeting.mp4", output_dir="uploads")
    """

    def __init__(self, sample_rate: int = 16000):
        """
        Args:
            sample_rate: Output WAV ka sample rate (Hz).
                         Whisper ke liye 16000 Hz recommended hai.
        """
        self.sample_rate = sample_rate
        self._check_ffmpeg()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def extract(self, input_path: str, output_dir: str = "uploads") -> str:
        """
        Input file se audio extract karke WAV file return karta hai.

        Args:
            input_path: Source video/audio file ka path.
            output_dir: Extracted audio save karne ki directory.

        Returns:
            Extracted WAV file ka path.

        Raises:
            FileNotFoundError: Agar input file exist nahi karta.
            ValueError: Agar format supported nahi hai.
            RuntimeError: Agar FFmpeg extraction fail kare.
        """
        input_path = Path(input_path)

        if not input_path.exists():
            raise FileNotFoundError(f"Input file nahi mila: {input_path}")

        suffix = input_path.suffix.lower()
        if suffix not in ALL_SUPPORTED_FORMATS:
            raise ValueError(
                f"Unsupported format '{suffix}'. "
                f"Supported: {sorted(ALL_SUPPORTED_FORMATS)}"
            )

        # Agar already audio hai to direct copy (still re-encode for consistency)
        os.makedirs(output_dir, exist_ok=True)
        output_path = Path(output_dir) / (input_path.stem + "_extracted.wav")

        logger.info("Audio extract ho raha hai: %s → %s", input_path, output_path)

        self._run_ffmpeg(str(input_path), str(output_path))

        logger.info("Extraction complete! Size: %.1f MB", output_path.stat().st_size / 1e6)
        return str(output_path)

    def get_duration(self, file_path: str) -> float:
        """
        Audio/video file ki duration seconds mein return karta hai.

        Args:
            file_path: Media file ka path.

        Returns:
            Duration in seconds (float).
        """
        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            file_path,
        ]
        try:
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
                text=True,
            )
            return float(result.stdout.strip())
        except (subprocess.CalledProcessError, ValueError) as exc:
            logger.warning("Duration detect nahi hua: %s", exc)
            return 0.0

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _run_ffmpeg(self, input_path: str, output_path: str) -> None:
        """
        FFmpeg command run karta hai audio extract karne ke liye.
        Mono, 16 kHz WAV output produce karta hai jo Whisper ke liye optimal hai.
        """
        cmd = [
            "ffmpeg",
            "-y",                       # Overwrite without asking
            "-i", input_path,
            "-vn",                       # No video
            "-acodec", "pcm_s16le",      # 16-bit PCM
            "-ar", str(self.sample_rate),# Sample rate
            "-ac", "1",                  # Mono channel
            output_path,
        ]

        try:
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
            )
            logger.debug("FFmpeg stdout: %s", result.stdout.decode(errors="replace"))
        except subprocess.CalledProcessError as exc:
            err_msg = exc.stderr.decode(errors="replace")
            logger.error("FFmpeg error:\n%s", err_msg)
            raise RuntimeError(
                f"Audio extraction fail ho gaya.\nFFmpeg error:\n{err_msg}"
            ) from exc

    @staticmethod
    def _check_ffmpeg() -> None:
        """Verify karta hai ki FFmpeg system mein install hai."""
        try:
            subprocess.run(
                ["ffmpeg", "-version"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True,
            )
        except (subprocess.CalledProcessError, FileNotFoundError) as exc:
            raise EnvironmentError(
                "FFmpeg nahi mila! Please install karo:\n"
                "  Ubuntu/Debian: sudo apt install ffmpeg\n"
                "  Mac:           brew install ffmpeg\n"
                "  Windows:       https://ffmpeg.org/download.html"
            ) from exc
