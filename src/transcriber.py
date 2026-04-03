"""
transcriber.py
==============
OpenAI Whisper ka use karke meeting audio/video ko text mein convert karta hai.
Hindi, English, aur Hinglish (mixed) language support hai.
Long meetings ke liye chunked processing implement ki gayi hai.
"""

import os
import logging
import math
import tempfile
from pathlib import Path
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

# Default chunk size: 10 minutes (Whisper API limit ke neeche rehne ke liye)
DEFAULT_CHUNK_SECONDS = int(os.getenv("CHUNK_DURATION_SECONDS", "600"))


class Transcriber:
    """
    Whisper model se audio/video files ko transcribe karta hai.

    Long meetings (2+ hours) ke liye audio ko chunks mein split karta hai,
    har chunk ko transcribe karta hai, aur sab ko merge karta hai.

    Usage::

        transcriber = Transcriber(model_size="medium")
        result = transcriber.transcribe("meeting.wav")
        print(result["text"])       # Full transcript
        print(result["segments"])   # Timestamped segments
    """

    def __init__(
        self,
        model_size: Optional[str] = None,
        language: Optional[str] = None,
        chunk_duration: int = DEFAULT_CHUNK_SECONDS,
        progress_callback=None,
    ):
        """
        Args:
            model_size: Whisper model - tiny/base/small/medium/large/large-v2/large-v3
                        Hindi ke liye medium ya large recommended hai.
            language:   Transcription language code (e.g. 'hi', 'en').
                        None rakhne par Whisper auto-detect karega.
            chunk_duration: Long audio ke liye chunk size in seconds.
            progress_callback: Optional callable(step: int, total: int, msg: str)
                               for progress updates in UI.
        """
        self.model_size = model_size or os.getenv("WHISPER_MODEL", "medium")
        self.language = language or os.getenv("TRANSCRIPTION_LANGUAGE") or None
        self.chunk_duration = chunk_duration
        self.progress_callback = progress_callback
        self._model = None  # Lazy load - pehli call par load hoga

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def transcribe(self, audio_path: str) -> Dict[str, Any]:
        """
        Audio file ko transcribe karta hai.

        Short files directly transcribe hote hain.
        Long files automatically chunks mein split ho jaate hain.

        Args:
            audio_path: WAV/MP3 audio file ka path.

        Returns:
            dict with keys:
                - "text": str - Full transcript
                - "segments": list[dict] - Timestamped segments
                - "language": str - Detected/used language
                - "duration": float - Audio duration in seconds
                - "chunks_processed": int - Number of chunks processed
        """
        audio_path = Path(audio_path)
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file nahi mila: {audio_path}")

        duration = self._get_audio_duration(str(audio_path))
        logger.info(
            "Transcription shuru: %s (%.1f min)", audio_path.name, duration / 60
        )

        # Short meeting (under chunk threshold) - direct transcribe
        if duration <= self.chunk_duration:
            return self._transcribe_file(str(audio_path), duration, chunk_index=0, total_chunks=1)

        # Long meeting - chunked processing
        return self._transcribe_chunked(str(audio_path), duration)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _load_model(self):
        """Whisper model lazy-load karta hai (only once)."""
        if self._model is None:
            try:
                import whisper
            except ImportError as exc:
                raise ImportError(
                    "openai-whisper install nahi hai! "
                    "Run: pip install openai-whisper"
                ) from exc

            logger.info("Whisper '%s' model load ho raha hai...", self.model_size)
            self._update_progress(0, 1, f"Whisper '{self.model_size}' model load ho raha hai...")
            self._model = whisper.load_model(self.model_size)
            logger.info("Model load ho gaya!")
        return self._model

    def _transcribe_file(
        self,
        audio_path: str,
        duration: float,
        chunk_index: int = 0,
        total_chunks: int = 1,
    ) -> Dict[str, Any]:
        """Single audio file/chunk transcribe karta hai."""
        model = self._load_model()

        self._update_progress(
            chunk_index,
            total_chunks,
            f"Transcribing chunk {chunk_index + 1}/{total_chunks}...",
        )

        # Transcription options
        options: Dict[str, Any] = {
            "fp16": False,          # CPU compatibility ke liye
            "verbose": False,
            "word_timestamps": False,
        }
        if self.language:
            options["language"] = self.language

        result = model.transcribe(audio_path, **options)

        return {
            "text": result.get("text", "").strip(),
            "segments": result.get("segments", []),
            "language": result.get("language", "unknown"),
            "duration": duration,
            "chunks_processed": 1,
        }

    def _transcribe_chunked(self, audio_path: str, duration: float) -> Dict[str, Any]:
        """
        Long audio ko chunks mein split karke transcribe karta hai.
        Har chunk ka time offset adjust karke segments merge karta hai.
        """
        try:
            from pydub import AudioSegment
        except ImportError as exc:
            raise ImportError(
                "pydub install nahi hai! Run: pip install pydub"
            ) from exc

        num_chunks = math.ceil(duration / self.chunk_duration)
        logger.info(
            "Long meeting detected (%.1f min). %d chunks mein process hoga.",
            duration / 60,
            num_chunks,
        )

        audio = AudioSegment.from_file(audio_path)
        all_text: List[str] = []
        all_segments: List[Dict] = []
        detected_language = "unknown"

        with tempfile.TemporaryDirectory() as tmp_dir:
            for i in range(num_chunks):
                start_ms = i * self.chunk_duration * 1000
                end_ms = min((i + 1) * self.chunk_duration * 1000, len(audio))
                chunk_audio = audio[start_ms:end_ms]

                chunk_path = os.path.join(tmp_dir, f"chunk_{i:03d}.wav")
                chunk_audio.export(chunk_path, format="wav")

                chunk_duration_sec = (end_ms - start_ms) / 1000
                result = self._transcribe_file(
                    chunk_path, chunk_duration_sec, chunk_index=i, total_chunks=num_chunks
                )

                all_text.append(result["text"])
                detected_language = result["language"]

                # Adjust timestamps for the offset of this chunk
                time_offset = i * self.chunk_duration
                for seg in result["segments"]:
                    adjusted_seg = dict(seg)
                    adjusted_seg["start"] = seg["start"] + time_offset
                    adjusted_seg["end"] = seg["end"] + time_offset
                    all_segments.append(adjusted_seg)

                logger.info(
                    "Chunk %d/%d done. Text length: %d chars",
                    i + 1,
                    num_chunks,
                    len(result["text"]),
                )

        full_text = " ".join(all_text)
        self._update_progress(num_chunks, num_chunks, "Transcription complete!")

        return {
            "text": full_text.strip(),
            "segments": all_segments,
            "language": detected_language,
            "duration": duration,
            "chunks_processed": num_chunks,
        }

    def _get_audio_duration(self, audio_path: str) -> float:
        """Audio file ki duration seconds mein return karta hai."""
        try:
            from pydub import AudioSegment
            audio = AudioSegment.from_file(audio_path)
            return len(audio) / 1000.0
        except Exception as exc:
            logger.warning("Duration detect nahi hua (pydub error): %s", exc)
            # Fallback: try ffprobe
            import subprocess
            try:
                result = subprocess.run(
                    [
                        "ffprobe", "-v", "error",
                        "-show_entries", "format=duration",
                        "-of", "default=noprint_wrappers=1:nokey=1",
                        audio_path,
                    ],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    check=True,
                )
                return float(result.stdout.strip())
            except Exception:
                return 0.0

    def _update_progress(self, step: int, total: int, msg: str) -> None:
        """UI callback ko progress update deta hai (agar provided ho)."""
        if self.progress_callback:
            try:
                self.progress_callback(step, total, msg)
            except Exception as exc:
                logger.debug("Progress callback error: %s", exc)
