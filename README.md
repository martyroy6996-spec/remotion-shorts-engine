# Remotion Shorts Engine

A Colab-first clipping and editing toolkit. The repository now has two workflows:

- **Podcast / interview workflow:** the original Gemini + faster-whisper + HyperFrames + Remotion path in `colab/Reel_Factory.ipynb`.
- **GTA 6 gameplay review workflow:** a separate Colab notebook that reuses the existing GTA6_CLIPPING Drive project and completed transcript/candidate files.

This repository contains code only. Never commit API keys, source footage, transcripts, render files, or private media.

## GTA 6 Colab workflow (new)

Open the GTA 6 notebook from the `feature/gta6-colab-pipeline` branch:

https://colab.research.google.com/github/martyroy6996-spec/remotion-shorts-engine/blob/feature/gta6-colab-pipeline/colab/GTA6_Clip_Factory.ipynb

The notebook expects this existing Drive structure:

```
MyDrive/GTA6_CLIPPING/
  02_SOURCE_MEDIA/authorized_originals/GTA-6-Gameplay-SnapYT.App.mp4
  04_TRANSCRIPTS/
  05_CLIP_CANDIDATES/ranked_clip_candidates.csv
```

It mounts Drive, checks the source and candidate timecodes, extracts four visual review frames per candidate, and renders source-aspect review previews. It reuses the transcript and candidate CSV already created in Colab; it does not re-transcribe the source.

The helper implementation is `pipeline/gta6_review.py`. Its commands are:

```bash
python pipeline/gta6_review.py verify --video SOURCE.mp4 --candidates ranked_clip_candidates.csv
python pipeline/gta6_review.py inspect --video SOURCE.mp4 --candidates ranked_clip_candidates.csv --limit 20 --output visual_review
python pipeline/gta6_review.py previews --video SOURCE.mp4 --candidates ranked_clip_candidates.csv --limit 5 --seconds 45 --output previews
```

**Scope honesty:** this GTA 6 branch currently implements source validation, candidate timecode validation, contact-sheet extraction, and source-aspect review previews. It does not yet implement gameplay-aware automatic event detection, verified vertical reframing, final caption correction, or the GTA 6 Remotion/HyperFrames render pipeline. Those stages must be built and tested before calling this a complete automated clip factory.

## Original podcast / interview workflow

Open the original notebook on `main`:

https://colab.research.google.com/github/martyroy6996-spec/remotion-shorts-engine/blob/main/colab/Reel_Factory.ipynb

That workflow uses faster-whisper for word timing, Gemini to rank transcript-supported moments, HyperFrames + Three.js for a transparent motion-graphics overlay, and Remotion for final composition. It was designed around podcast/interview content and should not be assumed to be suitable for gameplay without adaptation.

## Engineering principles

- Colab is an execution environment, not permanent storage. Checkpoints and outputs belong in Drive.
- GPU availability is optional; never assume a Colab Free session has a T4.
- Existing user-generated transcripts and candidates should be reused when valid.
- Transcript scores are heuristics, not virality predictions. Human review of complete footage is required.
- Never force a centre crop on gameplay without checking where the action and HUD are located.
- Rendering and publishing remain separate. No automatic publishing without explicit approval.
- Do not publish third-party gameplay footage unless the user owns it, has permission, or has a valid legal basis to use it.

## Existing render stack

The original workflow uses Node.js, Remotion, HyperFrames, Three.js, and FFmpeg. HyperFrames renders a transparent WebM overlay; Remotion composites the overlay and source footage. Remotion licensing and current usage terms must be checked before commercial production: https://www.remotion.dev/docs/license/pricing
