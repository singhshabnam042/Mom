"""
main.py
=======
MoM Generator Bot - Command Line Interface (CLI)
Meeting recording ko directly process karo without web UI.

Usage examples:
    python main.py --input meeting.mp4 --output mom.pdf
    python main.py --input meeting.mp3 --format docx
    python main.py --input meeting.mp4 --format all
    python main.py --input recording.wav --whisper-model large --gpt-model gpt-4
"""

import argparse
import logging
import os
import sys
import time
from pathlib import Path
from datetime import datetime

from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.audio_extractor import AudioExtractor, ALL_SUPPORTED_FORMATS
from src.transcriber import Transcriber
from src.summarizer import MoMSummarizer
from src.document_generator import DocumentGenerator
from src.utils import ensure_dirs, format_duration, setup_logging, get_file_size_mb


def parse_args() -> argparse.Namespace:
    """CLI arguments parse karta hai."""
    parser = argparse.ArgumentParser(
        prog="mom-generator",
        description="🎙️ Meeting Recording → Minutes of Meeting (MoM) Generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --input meeting.mp4
  python main.py --input meeting.mp4 --output mom_report --format pdf
  python main.py --input meeting.mp3 --format all --whisper-model large
  python main.py --input meeting.mp4 --gpt-model gpt-3.5-turbo --verbose
        """,
    )

    # Required
    parser.add_argument(
        "--input", "-i",
        required=True,
        metavar="FILE",
        help="Input video/audio file path (MP4, MKV, AVI, MOV, WEBM, MP3, WAV, M4A, OGG)",
    )

    # Optional
    parser.add_argument(
        "--output", "-o",
        default=None,
        metavar="NAME",
        help="Output filename (without extension). Default: MoM_<timestamp>",
    )
    parser.add_argument(
        "--format", "-f",
        default="pdf",
        choices=["pdf", "docx", "markdown", "all"],
        help="Output format: pdf, docx, markdown, or all (default: pdf)",
    )
    parser.add_argument(
        "--output-dir",
        default=os.getenv("OUTPUT_DIR", "outputs"),
        metavar="DIR",
        help="Directory to save output files (default: outputs/)",
    )
    parser.add_argument(
        "--whisper-model",
        default=os.getenv("WHISPER_MODEL", "medium"),
        choices=["tiny", "base", "small", "medium", "large", "large-v2", "large-v3"],
        help="Whisper model size (default: medium). Hindi ke liye: large recommended",
    )
    parser.add_argument(
        "--gpt-model",
        default=os.getenv("GPT_MODEL", "gpt-4"),
        choices=["gpt-4", "gpt-4-turbo", "gpt-3.5-turbo"],
        help="OpenAI GPT model (default: gpt-4)",
    )
    parser.add_argument(
        "--language",
        default=os.getenv("TRANSCRIPTION_LANGUAGE", ""),
        metavar="LANG",
        help="Transcription language code: hi, en, or empty for auto-detect",
    )
    parser.add_argument(
        "--api-key",
        default=os.getenv("OPENAI_API_KEY", ""),
        metavar="KEY",
        help="OpenAI API key (or set OPENAI_API_KEY env var)",
    )
    parser.add_argument(
        "--save-transcript",
        action="store_true",
        help="Transcript bhi save karo (.txt file mein)",
    )
    parser.add_argument(
        "--transcript-only",
        action="store_true",
        help="Sirf transcript generate karo, MoM nahi (useful for testing)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output (DEBUG level logging)",
    )

    return parser.parse_args()


def print_banner() -> None:
    """Welcome banner print karta hai."""
    print("\n" + "=" * 65)
    print("  🎙️  MoM Generator Bot - Meeting → Minutes of Meeting")
    print("=" * 65 + "\n")


def print_step(step: int, total: int, msg: str) -> None:
    """Progress step print karta hai."""
    bar_filled = int((step / max(total, 1)) * 20)
    bar = "█" * bar_filled + "░" * (20 - bar_filled)
    pct = int((step / max(total, 1)) * 100)
    print(f"  [{bar}] {pct:3d}%  {msg}", flush=True)


def main() -> int:
    """Main CLI function. Returns exit code (0 = success, 1 = error)."""
    args = parse_args()

    # Setup logging
    setup_logging("DEBUG" if args.verbose else "INFO")
    logger = logging.getLogger(__name__)

    print_banner()

    # ── Validate inputs ────────────────────────────────────────────
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"❌ Error: File nahi mila - {args.input}", file=sys.stderr)
        return 1

    if input_path.suffix.lower() not in ALL_SUPPORTED_FORMATS:
        print(
            f"❌ Error: Unsupported format '{input_path.suffix}'\n"
            f"   Supported: {sorted(ALL_SUPPORTED_FORMATS)}",
            file=sys.stderr,
        )
        return 1

    if not args.transcript_only and not args.api_key:
        print(
            "❌ Error: OpenAI API key required!\n"
            "   Option 1: .env file mein OPENAI_API_KEY set karo\n"
            "   Option 2: --api-key flag use karo\n"
            "   API key: https://platform.openai.com/api-keys",
            file=sys.stderr,
        )
        return 1

    # Ensure output dirs
    ensure_dirs(args.output_dir, "uploads")

    file_size = get_file_size_mb(str(input_path))
    print(f"📁 Input: {input_path.name} ({file_size:.1f} MB)")
    print(f"🤖 Models: Whisper={args.whisper_model}, GPT={args.gpt_model}")
    print(f"📂 Output dir: {args.output_dir}\n")

    start_time = time.time()
    output_filename = args.output or f"MoM_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    # ── Step 1: Extract Audio ──────────────────────────────────────
    print("Step 1/3: Audio Extraction")
    print_step(0, 3, "FFmpeg se audio extract ho raha hai...")

    try:
        extractor = AudioExtractor()
        audio_path = extractor.extract(str(input_path), output_dir="uploads")
        duration = extractor.get_duration(audio_path)
        print_step(1, 3, f"Audio ready ({format_duration(duration)})")
        print(f"          → {audio_path}\n")
    except EnvironmentError as exc:
        print(f"\n❌ FFmpeg Error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"\n❌ Audio extraction fail: {exc}", file=sys.stderr)
        return 1

    # ── Step 2: Transcribe ─────────────────────────────────────────
    print("Step 2/3: Transcription (Whisper)")
    print_step(0, 3, f"Whisper '{args.whisper_model}' model load ho raha hai...")

    def transcription_progress(step, total, msg):
        print_step(step, total, msg)

    try:
        transcriber = Transcriber(
            model_size=args.whisper_model,
            language=args.language if args.language else None,
            progress_callback=transcription_progress,
        )
        transcript_result = transcriber.transcribe(audio_path)
        transcript_text = transcript_result["text"]
        chunks = transcript_result["chunks_processed"]
        lang = transcript_result["language"]

        print(f"\n          → Language: {lang}")
        print(f"          → Chunks processed: {chunks}")
        print(f"          → Transcript length: {len(transcript_text)} chars\n")

        if not transcript_text.strip():
            print("❌ Error: Transcript empty hai! Audio check karo.", file=sys.stderr)
            return 1

        # Save transcript if requested
        if args.save_transcript or args.transcript_only:
            transcript_file = Path(args.output_dir) / f"{output_filename}_transcript.txt"
            transcript_file.write_text(transcript_text, encoding="utf-8")
            print(f"📜 Transcript saved: {transcript_file}")

        if args.transcript_only:
            print("\n✅ Transcript-only mode. Done!")
            return 0

    except Exception as exc:
        print(f"\n❌ Transcription fail: {exc}", file=sys.stderr)
        if args.verbose:
            logger.exception("Transcription error details")
        return 1

    # ── Step 3: Generate MoM ───────────────────────────────────────
    print("Step 3/3: MoM Generation (GPT)")
    print_step(0, 3, "GPT ko transcript bheja ja raha hai...")

    def mom_progress(step, total, msg):
        print_step(step, total, msg)

    try:
        summarizer = MoMSummarizer(
            model=args.gpt_model,
            api_key=args.api_key,
            progress_callback=mom_progress,
        )
        mom_result = summarizer.generate(
            transcript=transcript_text,
            meeting_date=datetime.now().strftime("%Y-%m-%d"),
            duration_seconds=duration,
        )
        mom_text = mom_result["formatted"]
        print(f"\n          → Model used: {mom_result['model_used']}")
        print(f"          → Chunks used: {mom_result['chunks_used']}\n")
    except ValueError as exc:
        print(f"\n❌ Config error: {exc}", file=sys.stderr)
        return 1
    except RuntimeError as exc:
        print(f"\n❌ GPT error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"\n❌ MoM generation fail: {exc}", file=sys.stderr)
        if args.verbose:
            logger.exception("MoM generation error details")
        return 1

    # ── Save Documents ─────────────────────────────────────────────
    print("📄 Documents saving...")
    gen = DocumentGenerator(output_dir=args.output_dir)
    saved_files = []

    fmt = args.format
    try:
        if fmt in ("pdf", "all"):
            path = gen.to_pdf(mom_text, filename=output_filename)
            saved_files.append(path)
            print(f"   ✅ PDF:      {path}")

        if fmt in ("docx", "all"):
            path = gen.to_docx(mom_text, filename=output_filename)
            saved_files.append(path)
            print(f"   ✅ Word:     {path}")

        if fmt in ("markdown", "all"):
            path = gen.to_markdown(mom_text, filename=output_filename)
            saved_files.append(path)
            print(f"   ✅ Markdown: {path}")
    except Exception as exc:
        print(f"\n❌ Document save fail: {exc}", file=sys.stderr)
        return 1

    # ── Cleanup temp audio ─────────────────────────────────────────
    try:
        os.remove(audio_path)
    except OSError:
        pass

    # ── Summary ────────────────────────────────────────────────────
    elapsed = time.time() - start_time
    print("\n" + "=" * 65)
    print(f"  🎉 Done! Processing time: {format_duration(elapsed)}")
    print(f"  🎙️  Meeting duration: {format_duration(duration)}")
    print(f"  📄 Files saved: {len(saved_files)}")
    for f in saved_files:
        print(f"     → {f}")
    print("=" * 65 + "\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
