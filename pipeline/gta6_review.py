#!/usr/bin/env python3
"""GTA 6 gameplay clip review helpers for Google Colab.

This module deliberately does not claim that transcript scores predict virality.
It reuses existing transcript/candidate artifacts, extracts review frames, and
creates source-aspect preview files without destructive cropping.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import shutil
import subprocess
from pathlib import Path
from typing import Any

OFFSETS = (5, 15, 25, 35)


def run(command: list[str]) -> None:
    print("$", " ".join(map(str, command)), flush=True)
    subprocess.run(command, check=True)


def probe_duration(video: Path) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(video)],
        capture_output=True, text=True, check=True
    )
    return float(result.stdout.strip())


def load_candidates(path: Path, limit: int) -> list[dict[str, Any]]:
    if not path.is_file():
        raise FileNotFoundError(f"Candidate CSV not found: {path}")
    with path.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    for row in rows:
        row["start"] = float(row["start"])
        row["end"] = float(row["end"])
        row["score"] = float(row.get("score", 0))
    rows.sort(key=lambda row: row["score"], reverse=True)
    return rows[:limit]


def verify(args: argparse.Namespace) -> None:
    video = Path(args.video)
    candidate_csv = Path(args.candidates)
    duration = probe_duration(video)
    rows = load_candidates(candidate_csv, args.limit)
    print(f"Source: {video.name}")
    print(f"Duration: {duration:.2f}s ({duration / 60:.2f} min)")
    print(f"Candidate rows: {len(rows)}")
    for index, row in enumerate(rows, 1):
        if row["start"] < 0 or row["end"] <= row["start"] or row["end"] > duration + 1:
            raise ValueError(f"Invalid candidate #{index}: {row}")
    print("Candidate timestamps: valid within source duration.")
    print("Verification passed.")


def inspect(args: argparse.Namespace) -> None:
    from PIL import Image, ImageDraw, ImageFont

    video = Path(args.video)
    candidate_csv = Path(args.candidates)
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    rows = load_candidates(candidate_csv, args.limit)
    duration = probe_duration(video)

    width, height, label_h = 320, 180, 32
    group_size = 5
    font = ImageFont.load_default()
    sheet = None
    draw = None

    for index, row in enumerate(rows, 1):
        start = row["start"]
        if start + max(OFFSETS) >= duration:
            print(f"Skipping candidate {index}: frame offset exceeds source.")
            continue

        group_pos = (index - 1) % group_size
        if group_pos == 0:
            sheet = Image.new("RGB", (width * 4, (height + label_h) * group_size), "black")
            draw = ImageDraw.Draw(sheet)

        y = group_pos * (height + label_h)
        draw.text((8, y + 5), f"Candidate {index} | {start/60:05.2f} min | score {row['score']}", fill="white", font=font)

        for col, offset in enumerate(OFFSETS):
            frame_path = out / f"candidate_{index:02d}_{offset:02d}s.jpg"
            run([
                "ffmpeg", "-y", "-v", "error", "-ss", f"{start + offset:.3f}",
                "-i", str(video), "-frames:v", "1", "-vf", f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2",
                "-q:v", "3", str(frame_path)
            ])
            with Image.open(frame_path) as frame:
                sheet.paste(frame.convert("RGB"), (col * width, y + label_h))
            draw.text((col * width + 8, y + label_h + 7), f"+{offset}s", fill="yellow", font=font)

        if group_pos == group_size - 1 or index == len(rows):
            sheet_path = out / f"visual_contact_sheet_{(index - 1)//group_size + 1}.jpg"
            sheet.save(sheet_path, quality=90)
            print("Saved:", sheet_path)

    print(f"Visual review assets saved to: {out}")


def previews(args: argparse.Namespace) -> None:
    video = Path(args.video)
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    rows = load_candidates(Path(args.candidates), args.limit)
    for rank, row in enumerate(rows, 1):
        start = row["start"]
        duration = min(args.seconds, row["end"] - row["start"])
        target = out / f"candidate_{rank:02d}_preview.mp4"
        if target.exists() and target.stat().st_size > 100_000 and not args.overwrite:
            print("Keeping existing preview:", target)
            continue
        run([
            "ffmpeg", "-y", "-v", "error", "-ss", f"{start:.3f}", "-i", str(video),
            "-t", f"{duration:.3f}", "-map", "0:v:0", "-map", "0:a:0?",
            "-vf", "scale=960:-2:force_original_aspect_ratio=decrease",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "25",
            "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k",
            "-movflags", "+faststart", str(target)
        ])
        print("Saved:", target)
    print(f"Previews saved to: {out}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--video", required=True)
    common.add_argument("--candidates", required=True)
    common.add_argument("--limit", type=int, default=20)

    p = sub.add_parser("verify", parents=[common])
    p.set_defaults(func=verify)

    p = sub.add_parser("inspect", parents=[common])
    p.add_argument("--output", required=True)
    p.set_defaults(func=inspect)

    p = sub.add_parser("previews", parents=[common])
    p.add_argument("--output", required=True)
    p.add_argument("--seconds", type=float, default=45)
    p.add_argument("--overwrite", action="store_true")
    p.set_defaults(func=previews)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
