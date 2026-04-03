"""
summarizer.py
=============
GPT-4/3.5 ka use karke meeting transcript se structured
Minutes of Meeting (MoM) generate karta hai.
Hindi, English, aur Hinglish (mixed) language support hai.
Long transcripts ke liye chunked summarization implement ki gayi hai.
"""

import math
import os
import logging
from datetime import datetime
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# MoM generation prompt (works for both Hindi and English)
MOM_SYSTEM_PROMPT = """You are an expert professional meeting secretary who creates structured
Minutes of Meeting (MoM) documents. You understand Hindi, English, and Hinglish (mixed) content.

Your job is to analyze meeting transcripts and extract:
1. Key discussion points (not verbatim, but summarized)
2. Action items with owner names if mentioned
3. Decisions made during the meeting
4. Open issues / pending items
5. Participants (identify from conversation context)
6. Next steps / follow-ups

Be concise, professional, and accurate. If something is not mentioned in the transcript,
write "Not mentioned" rather than guessing."""

MOM_USER_PROMPT_TEMPLATE = """Please analyze the following meeting transcript and generate a structured 
Minutes of Meeting (MoM) document.

TRANSCRIPT:
{transcript}

---
Please generate the MoM in the following EXACT format (keep the emoji headers):

📅 **MEETING DATE & TIME**
[Extract if mentioned, otherwise write "Not mentioned in recording"]

⏱️ **DURATION**
[Approximate duration based on transcript length or context]

👥 **PARTICIPANTS IDENTIFIED**
[List all names/speakers mentioned in the transcript]

📌 **KEY DISCUSSION POINTS**
[Numbered list of main topics discussed - be concise but complete]

✅ **ACTION ITEMS**
[Numbered list - format: "Owner Name: Action description" or "Action description (Owner: TBD)"]

📝 **DECISIONS MADE**
[Numbered list of confirmed decisions from the meeting]

⚠️ **OPEN ISSUES / PENDING ITEMS**
[Numbered list of unresolved issues, waiting items, or pending decisions]

📆 **NEXT STEPS / FOLLOW-UPS**
[Numbered list of next steps, deadlines, or scheduled follow-up meetings]

---
Note: The transcript may be in Hindi, English, or mixed Hinglish. Generate the MoM in English
for professional documentation, but keep names and technical terms as-is."""

# Chunk size for long transcripts (GPT context window safety)
MAX_TRANSCRIPT_CHARS = 12000  # ~3000 tokens, safe for gpt-3.5-turbo (4k context)
MAX_TRANSCRIPT_CHARS_GPT4 = 30000  # ~7500 tokens, safe for gpt-4


class MoMSummarizer:
    """
    OpenAI GPT se meeting transcript ka MoM generate karta hai.

    Usage::

        summarizer = MoMSummarizer()
        mom = summarizer.generate(transcript_text, meeting_date="2024-01-15")
        print(mom["formatted"])  # Formatted MoM document
    """

    def __init__(
        self,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        progress_callback=None,
    ):
        """
        Args:
            model: GPT model name - gpt-4, gpt-4-turbo, gpt-3.5-turbo
            api_key: OpenAI API key (ya .env mein OPENAI_API_KEY set karo)
            progress_callback: Optional callable(step, total, msg) for UI updates
        """
        self.model = model or os.getenv("GPT_MODEL", "gpt-4")
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self.progress_callback = progress_callback

        if not self.api_key:
            raise ValueError(
                "OpenAI API key nahi mili!\n"
                "1. .env file mein OPENAI_API_KEY=sk-... set karo\n"
                "2. Ya environment variable set karo: export OPENAI_API_KEY=sk-...\n"
                "3. API key lene ke liye: https://platform.openai.com/api-keys"
            )

        # Max chars based on model
        if "gpt-4" in self.model:
            self._max_chars = MAX_TRANSCRIPT_CHARS_GPT4
        else:
            self._max_chars = MAX_TRANSCRIPT_CHARS

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate(
        self,
        transcript: str,
        meeting_date: Optional[str] = None,
        duration_seconds: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Transcript se structured MoM generate karta hai.

        Args:
            transcript: Meeting ka full text transcript.
            meeting_date: Meeting ki date string (optional).
            duration_seconds: Meeting ki duration (optional).

        Returns:
            dict with keys:
                - "formatted": str - Complete formatted MoM text
                - "model_used": str - GPT model used
                - "transcript_length": int - Characters in transcript
                - "chunks_used": int - Chunks used for long transcripts
        """
        if not transcript or not transcript.strip():
            raise ValueError("Transcript empty hai! Pehle transcription karo.")

        self._update_progress(0, 3, "GPT se MoM generate ho raha hai...")

        # Add context (date/duration) to beginning of transcript
        context_prefix = self._build_context_prefix(meeting_date, duration_seconds)
        full_transcript = context_prefix + transcript

        # Check if transcript needs chunking
        if len(full_transcript) <= self._max_chars:
            mom_text = self._generate_single(full_transcript)
            chunks_used = 1
        else:
            mom_text = self._generate_chunked(full_transcript)
            chunks_used = math.ceil(len(full_transcript) / self._max_chars)

        self._update_progress(3, 3, "MoM ready hai!")

        return {
            "formatted": mom_text,
            "model_used": self.model,
            "transcript_length": len(transcript),
            "chunks_used": chunks_used,
        }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _get_client(self):
        """OpenAI client initialize karta hai."""
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise ImportError(
                "openai library install nahi hai! Run: pip install openai"
            ) from exc
        return OpenAI(api_key=self.api_key)

    def _generate_single(self, transcript: str) -> str:
        """
        Single API call se MoM generate karta hai (short transcripts ke liye).
        """
        client = self._get_client()
        self._update_progress(1, 3, "GPT ko transcript bheja ja raha hai...")

        prompt = MOM_USER_PROMPT_TEMPLATE.format(transcript=transcript)

        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": MOM_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,  # Lower temp = more consistent output
                max_tokens=2000,
            )
            self._update_progress(2, 3, "MoM text receive hua...")
            return response.choices[0].message.content.strip()
        except Exception as exc:
            logger.error("GPT API call fail ho gaya: %s", exc)
            raise RuntimeError(
                f"MoM generation fail hua: {exc}\n"
                "Check karo: API key valid hai, aur credit available hai."
            ) from exc

    def _generate_chunked(self, transcript: str) -> str:
        """
        Long transcript ko chunks mein process karta hai,
        phir final MoM ek combined summary se generate karta hai.
        """
        logger.info(
            "Long transcript (%d chars). Chunked processing shuru...",
            len(transcript),
        )

        chunks = []
        for i in range(0, len(transcript), self._max_chars):
            chunks.append(transcript[i : i + self._max_chars])

        num_chunks = len(chunks)
        partial_summaries = []

        # Step 1: Extract key points from each chunk
        for idx, chunk in enumerate(chunks):
            self._update_progress(
                idx, num_chunks + 1, f"Chunk {idx + 1}/{num_chunks} process ho raha hai..."
            )
            summary = self._extract_partial_summary(chunk, idx + 1, num_chunks)
            partial_summaries.append(summary)

        # Step 2: Combine all partial summaries into final MoM
        self._update_progress(num_chunks, num_chunks + 1, "Final MoM compile ho raha hai...")
        combined = "\n\n".join(partial_summaries)
        return self._compile_final_mom(combined)

    def _extract_partial_summary(self, chunk: str, chunk_num: int, total: int) -> str:
        """Ek transcript chunk se raw summary extract karta hai."""
        client = self._get_client()
        prompt = (
            f"This is part {chunk_num} of {total} of a meeting transcript.\n"
            "Extract ALL important information: key discussion points, action items, decisions, "
            "participant names, open issues, and next steps mentioned in this segment.\n\n"
            "Be thorough - do not miss any important information.\n\n"
            f"TRANSCRIPT SEGMENT:\n{chunk}"
        )

        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": MOM_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=1500,
            )
            return response.choices[0].message.content.strip()
        except Exception as exc:
            logger.error("Chunk %d processing fail: %s", chunk_num, exc)
            raise RuntimeError(f"Chunk {chunk_num} fail hua: {exc}") from exc

    def _compile_final_mom(self, combined_summaries: str) -> str:
        """Partial summaries ko combine karke final structured MoM banata hai."""
        client = self._get_client()
        # Build the format instructions (reuse the structure from user prompt)
        format_instructions = MOM_USER_PROMPT_TEMPLATE.split("TRANSCRIPT:")[1].strip()
        prompt = (
            "Below are summaries extracted from different parts of a long meeting transcript.\n"
            "Compile these into ONE cohesive, structured Minutes of Meeting (MoM) document.\n"
            "Merge duplicate items, remove redundancy, and organize clearly.\n\n"
            f"PARTIAL SUMMARIES:\n{combined_summaries}\n\n"
            f"{format_instructions}"
        )

        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": MOM_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=2000,
            )
            return response.choices[0].message.content.strip()
        except Exception as exc:
            logger.error("Final MoM compilation fail: %s", exc)
            raise RuntimeError(f"Final MoM compilation fail: {exc}") from exc

    @staticmethod
    def _build_context_prefix(
        meeting_date: Optional[str], duration_seconds: Optional[float]
    ) -> str:
        """Meeting metadata prefix banata hai jo transcript ke upar add hota hai."""
        lines = []
        if meeting_date:
            lines.append(f"Meeting Date: {meeting_date}")
        else:
            lines.append(f"Recording processed on: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

        if duration_seconds and duration_seconds > 0:
            mins = int(duration_seconds // 60)
            secs = int(duration_seconds % 60)
            lines.append(f"Meeting Duration: {mins} minutes {secs} seconds")

        if lines:
            return "[MEETING METADATA]\n" + "\n".join(lines) + "\n\n[TRANSCRIPT]\n"
        return ""

    def _update_progress(self, step: int, total: int, msg: str) -> None:
        """UI progress callback ko update karta hai."""
        if self.progress_callback:
            try:
                self.progress_callback(step, total, msg)
            except Exception as exc:
                logger.debug("Progress callback error: %s", exc)

