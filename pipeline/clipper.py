#!/usr/bin/env python3
"""Gemini-assisted clip selection and Remotion + HyperFrames rendering."""

from __future__ import annotations

import argparse
import html
import json
import math
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
FPS = 30


def run(command: list[str], cwd: Path | None = None) -> None:
    print("\n$", " ".join(str(part) for part in command), flush=True)
    subprocess.run(command, cwd=str(cwd or REPO), check=True)


def probe_duration(path: Path) -> float:
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
            capture_output=True, text=True, check=True
        )
        return float(result.stdout.strip())
    except Exception as exc:
        print("ffprobe could not read duration; estimating from transcript:", exc)
        return 0.0


def transcribe(path: Path, model_size: str) -> list[dict[str, Any]]:
    from faster_whisper import WhisperModel

    try:
        import torch
        has_gpu = torch.cuda.is_available()
    except Exception:
        has_gpu = False

    attempts = [("cuda", "float16"), ("cpu", "int8")] if has_gpu else [("cpu", "int8")]
    last_error = None
    segments = None

    for device, compute_type in attempts:
        try:
            print("Loading Whisper", model_size, "on", device, compute_type, flush=True)
            model = WhisperModel(
                model_size,
                device=device,
                compute_type=compute_type,
                download_root="/content/faster-whisper-cache"
            )
            segment_iter, info = model.transcribe(
                str(path),
                beam_size=5,
                word_timestamps=True,
                vad_filter=True,
                vad_parameters={"min_silence_duration_ms": 450}
            )
            segments = list(segment_iter)
            print("Language:", info.language, "| probability:", round(float(info.language_probability), 3))
            break
        except Exception as exc:
            last_error = exc
            print("Transcription attempt failed:", repr(exc), flush=True)

    if segments is None:
        raise RuntimeError("Whisper failed on available runtimes.") from last_error

    rows: list[dict[str, Any]] = []
    for segment in segments:
        segment_words = getattr(segment, "words", None)
        if segment_words:
            for word in segment_words:
                token = (word.word or "").strip()
                if token:
                    rows.append({
                        "start": round(float(word.start), 3),
                        "end": round(float(word.end), 3),
                        "text": token
                    })
        else:
            tokens = (segment.text or "").strip().split()
            if tokens:
                span = max(0.05, float(segment.end) - float(segment.start))
                step = span / len(tokens)
                for index, token in enumerate(tokens):
                    rows.append({
                        "start": round(float(segment.start) + index * step, 3),
                        "end": round(float(segment.start) + (index + 1) * step, 3),
                        "text": token
                    })

    if not rows:
        raise RuntimeError("Whisper returned no usable transcript words.")
    return rows


def gemini_candidates(
    words: list[dict[str, Any]],
    video_duration: float,
    model_name: str
) -> list[dict[str, Any]]:
    from google import genai
    from google.genai import types

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is missing. Add it to Colab Secrets or enter it in the notebook.")

    client = genai.Client(api_key=api_key)
    transcript = "\n".join(
        f"[{word['start']:.2f}s-{word['end']:.2f}s] {word['text']}" for word in words
    )

    schema = {
        "type": "OBJECT",
        "properties": {
            "clips": {
                "type": "ARRAY",
                "items": {
                    "type": "OBJECT",
                    "properties": {
                        "start_sec": {"type": "NUMBER"},
                        "end_sec": {"type": "NUMBER"},
                        "title": {"type": "STRING"},
                        "hook": {"type": "STRING"},
                        "reason": {"type": "STRING"},
                        "score": {"type": "INTEGER"},
                        "emphasis_words": {"type": "ARRAY", "items": {"type": "STRING"}}
                    },
                    "required": [
                        "start_sec", "end_sec", "title", "hook",
                        "reason", "score", "emphasis_words"
                    ]
                }
            }
        },
        "required": ["clips"]
    }

    prompt = f"""
You are a ruthless short-form podcast editor. Find the strongest self-contained moments
in this transcript for vertical 9:16 reels.

Return up to 7 candidates, ranked by score from 0 to 100.
Target 20-55 seconds per clip. A clip must make sense without the rest of the podcast.
Prefer a surprising claim, strong opinion, useful insight, conflict, story turn, funny beat,
revealing admission, or clear emotional change.
The first 1-2 seconds must make a viewer want to keep watching. Do not invent context,
facts, quotes, or dialogue. Do not manufacture a hook the speaker did not support.
Avoid long setups, repeated points, greetings, sponsor reads, and conclusions that need
missing context. Keep clips distinct; do not return overlapping versions of the same moment.

TIMESTAMP RULES:
- Every timestamp MUST be anchored to the supplied transcript timestamps.
- Start at the first necessary spoken word, not in the middle of a word.
- End after the complete thought, not in the middle of the final word.
- Do not make up timestamps. If a moment cannot be located precisely, skip it.
- Keep each clip between 15 and 65 seconds.
- Titles should be 2-5 words. Hooks should be concise and accurate.
- emphasis_words must contain only words actually spoken.

Video duration: {video_duration:.2f} seconds.

Transcript with word-level timecodes:
{transcript}
"""

    config = types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=schema,
        max_output_tokens=5000
    )
    response = client.models.generate_content(
        model=model_name,
        contents=prompt,
        config=config
    )
    raw = (response.text or "").strip()
    fence = chr(96) * 3
    if raw.startswith(fence):
        raw = re.sub(r"^" + fence + r"(?:json)?\s*|\s*" + fence + r"$", "", raw, flags=re.IGNORECASE)
    payload = json.loads(raw)

    valid: list[dict[str, Any]] = []
    for item in payload.get("clips", []):
        try:
            raw_start = max(0.0, float(item["start_sec"]))
            raw_end = min(video_duration or math.inf, float(item["end_sec"]))
            start_word = min(words, key=lambda w: abs(float(w["start"]) - raw_start))
            end_word = min(words, key=lambda w: abs(float(w["end"]) - raw_end))
            start = float(start_word["start"])
            end = float(end_word["end"])
            length = end - start
            if length < 15 or length > 65 or end <= start:
                continue

            candidate = {
                "start_sec": round(start, 3),
                "end_sec": round(end, 3),
                "duration_sec": round(length, 3),
                "title": str(item.get("title", "Strong moment")).strip()[:64],
                "hook": str(item.get("hook", "")).strip()[:120],
                "reason": str(item.get("reason", "")).strip()[:500],
                "score": max(0, min(100, int(item.get("score", 0)))),
                "emphasis_words": [
                    str(word).strip() for word in item.get("emphasis_words", [])
                    if str(word).strip()
                ][:12]
            }
            duplicate = False
            for existing in valid:
                overlap = max(
                    0.0,
                    min(candidate["end_sec"], existing["end_sec"])
                    - max(candidate["start_sec"], existing["start_sec"])
                )
                shorter = min(candidate["duration_sec"], existing["duration_sec"])
                if shorter > 0 and overlap / shorter > 0.60:
                    duplicate = True
                    break
            if not duplicate:
                valid.append(candidate)
        except (KeyError, TypeError, ValueError):
            continue

    valid.sort(key=lambda item: item["score"], reverse=True)
    for rank, item in enumerate(valid, start=1):
        item["rank"] = rank
    if not valid:
        raise RuntimeError("Gemini returned no valid 15-65 second clips. Inspect transcript.json or try another model.")
    return valid[:7]


def command_analyze(args: argparse.Namespace) -> None:
    source = Path(args.input).expanduser().resolve()
    workdir = Path(args.workdir).expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(f"Input video not found: {source}")
    workdir.mkdir(parents=True, exist_ok=True)

    duration = probe_duration(source)
    words = transcribe(source, args.whisper_model)
    if duration <= 0:
        duration = max(float(word["end"]) for word in words)

    transcript_path = workdir / "transcript.json"
    transcript_path.write_text(
        json.dumps({"source_name": source.name, "duration_sec": duration, "words": words}, indent=2),
        encoding="utf-8"
    )

    candidates = gemini_candidates(words, duration, args.gemini_model)
    analysis = {
        "source_name": source.name,
        "source_duration_sec": duration,
        "model": args.gemini_model,
        "whisper_model": args.whisper_model,
        "candidates": candidates
    }
    (workdir / "candidates.json").write_text(
        json.dumps(analysis, indent=2), encoding="utf-8"
    )
    print("\nRanked clip candidates:")
    for item in candidates:
        print(
            f"#{item['rank']} | score {item['score']} | "
            f"{item['start_sec']:.1f}-{item['end_sec']:.1f}s | "
            f"{item['title']} | {item['hook']}"
        )
    print("\nSaved:", transcript_path, "and", workdir / "candidates.json")


def build_captions(
    words: list[dict[str, Any]],
    start_sec: float,
    end_sec: float,
    emphasis_words: list[str]
) -> list[dict[str, Any]]:
    emphasis = {word.casefold().strip(".,!?;:\"'()[]") for word in emphasis_words}
    selected = [
        {
            "text": str(word["text"]).strip(),
            "start": max(0.0, float(word["start"]) - start_sec),
            "end": min(end_sec - start_sec, float(word["end"]) - start_sec)
        }
        for word in words
        if float(word["end"]) > start_sec and float(word["start"]) < end_sec
    ]

    groups: list[list[dict[str, Any]]] = []
    current: list[dict[str, Any]] = []
    for word in selected:
        pause = word["start"] - current[-1]["end"] if current else 0
        proposed = " ".join([part["text"] for part in current] + [word["text"]])
        if current and (len(current) >= 4 or len(proposed) > 26 or pause > 0.42):
            groups.append(current)
            current = []
        current.append(word)
    if current:
        groups.append(current)

    captions = []
    for group in groups:
        text = " ".join(part["text"] for part in group).strip()
        if not text:
            continue
        tokens = {token.casefold().strip(".,!?;:\"'()[]") for token in text.split()}
        captions.append({
            "text": text,
            "start": round(max(0.0, group[0]["start"]), 3),
            "end": round(max(group[-1]["end"], group[0]["start"] + 0.12), 3),
            "emphasis": bool(tokens.intersection(emphasis))
        })
    return captions


def safe_slug(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.lower()).strip("-")
    return slug[:42] or "podcast-clip"


def prepare_clip(source: Path, target: Path, start_sec: float, duration: float) -> None:
    # Normalize the selected excerpt to CFR 30fps so Remotion frame offsets
    # are exact even when the original podcast is 25, 29.97, 50, or 60fps.
    run([
        "ffmpeg", "-y", "-ss", f"{start_sec:.3f}", "-i", str(source),
        "-t", f"{duration:.3f}",
        "-map", "0:v:0", "-map", "0:a:0?",
        "-vf", "fps=30",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "19",
        "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart", str(target)
    ], REPO)


def command_render(args: argparse.Namespace) -> None:
    source = Path(args.input).expanduser().resolve()
    workdir = Path(args.workdir).expanduser().resolve()
    candidates_path = workdir / "candidates.json"
    transcript_path = workdir / "transcript.json"
    if not source.is_file():
        raise FileNotFoundError(f"Input video not found: {source}")
    if not candidates_path.is_file() or not transcript_path.is_file():
        raise FileNotFoundError("Run the analyze step before rendering.")

    analysis = json.loads(candidates_path.read_text(encoding="utf-8"))
    transcript = json.loads(transcript_path.read_text(encoding="utf-8"))
    candidates = analysis["candidates"]
    if args.candidate_index < 0 or args.candidate_index >= len(candidates):
        raise IndexError(f"candidate-index must be between 0 and {len(candidates) - 1}")
    clip = candidates[args.candidate_index]
    start_sec = float(clip["start_sec"])
    end_sec = float(clip["end_sec"])
    duration = end_sec - start_sec

    captions = build_captions(
        transcript["words"], start_sec, end_sec, clip.get("emphasis_words", [])
    )

    public_dir = REPO / "public"
    out_dir = REPO / "out"
    public_dir.mkdir(exist_ok=True)
    out_dir.mkdir(exist_ok=True)
    prepare_clip(source, public_dir / "source.mp4", start_sec, duration)

    template_path = REPO / "hyperframes" / "index.template.html"
    template = template_path.read_text(encoding="utf-8")
    title = html.escape(str(clip.get("title", "KEY MOMENT")).upper())
    overlay_html = (
        template
        .replace("__DURATION__", f"{duration:.3f}")
        .replace("__TITLE__", title)
    )
    (REPO / "hyperframes" / "index.html").write_text(overlay_html, encoding="utf-8")

    shutil.copy2(REPO / "node_modules" / "gsap" / "dist" / "gsap.min.js", REPO / "hyperframes" / "gsap.min.js")
    run(["npm", "run", "build:overlay"], REPO)
    run(["npx", "hyperframes", "lint"], REPO / "hyperframes")

    hyperframes_command = [
        "npx", "hyperframes", "render",
        "--format", "webm",
        "--output", "../public/overlay.webm"
    ]
    try:
        run(hyperframes_command + ["--gpu"], REPO / "hyperframes")
    except subprocess.CalledProcessError:
        print("HyperFrames GPU render failed; retrying with its default browser renderer.", flush=True)
        run(hyperframes_command, REPO / "hyperframes")

    props = {
        "sourceFile": "source.mp4",
        "overlayFile": "overlay.webm",
        "sourceStartSec": 0.0,
        "durationInSeconds": duration,
        "headline": clip.get("hook") or clip.get("title") or "KEY MOMENT",
        "captions": captions,
        "focalX": args.focal_x,
        "focalY": args.focal_y,
        "audioVolume": args.audio_volume
    }
    (public_dir / "props.json").write_text(
        json.dumps(props, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    filename = f"clip-{args.candidate_index + 1:02d}-{safe_slug(clip.get('title', 'podcast-clip'))}.mp4"
    local_output = out_dir / filename
    run([
        "npx", "remotion", "render",
        "src/index.ts", "ViralReel", str(local_output),
        "--props=public/props.json",
        "--codec=h264",
        "--crf=18"
    ], REPO)

    if not local_output.is_file() or local_output.stat().st_size == 0:
        raise RuntimeError("Remotion did not produce a non-empty MP4 file.")

    drive_output = Path(args.drive_output).expanduser()
    drive_output.mkdir(parents=True, exist_ok=True)
    final_path = drive_output / filename
    shutil.copy2(local_output, final_path)
    for metadata_file in [candidates_path, transcript_path]:
        shutil.copy2(metadata_file, drive_output / metadata_file.name)

    manifest = {
        "source": source.name,
        "output": filename,
        "clip": clip,
        "render_engine": {"final": "Remotion", "motion_graphics": "HyperFrames + Three.js"},
        "fps": FPS,
        "resolution": "1080x1920"
    }
    (drive_output / (Path(filename).stem + ".json")).write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("\nRENDER COMPLETE")
    print("Local:", local_output)
    print("Google Drive:", final_path)
    print("Size MB:", round(final_path.stat().st_size / (1024 * 1024), 2))


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    analyze = commands.add_parser("analyze", help="Transcribe and rank clip candidates.")
    analyze.add_argument("--input", required=True)
    analyze.add_argument("--workdir", required=True)
    analyze.add_argument("--whisper-model", default=os.environ.get("WHISPER_MODEL", "small"))
    analyze.add_argument("--gemini-model", default=os.environ.get("GEMINI_MODEL", "gemini-3.8-flash"))
    analyze.set_defaults(func=command_analyze)

    render = commands.add_parser("render", help="Render a selected candidate to Drive.")
    render.add_argument("--input", required=True)
    render.add_argument("--workdir", required=True)
    render.add_argument("--candidate-index", type=int, default=0)
    render.add_argument("--drive-output", required=True)
    render.add_argument("--focal-x", type=float, default=50)
    render.add_argument("--focal-y", type=float, default=50)
    render.add_argument("--audio-volume", type=float, default=1.0)
    render.set_defaults(func=command_render)
    return parser


if __name__ == "__main__":
    args = make_parser().parse_args()
    args.func(args)
