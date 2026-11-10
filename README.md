# Remotion Shorts Engine

A Colab-first podcast and long-form video clipping workflow. Upload a source video to Google Drive, let Whisper create word-timestamped transcription, use Gemini to rank self-contained moments, approve the clips, and render vertical MP4s with HyperFrames 3D overlays plus Remotion.

This repository contains code only. Do not commit API keys, source footage, transcripts, render files, or private media.

## What this version does

1. Reads video files from Google Drive / MyDrive / ReelFactory / input.
2. Transcribes speech with faster-whisper and word timestamps.
3. Asks Gemini to identify up to seven promising 15-65 second moments using transcript-supported timecodes.
4. Shows ranked candidates for human selection.
5. Uses HyperFrames and Three.js to render a transparent 3D motion-graphics overlay.
6. Uses Remotion to crop the speaker footage to 1080x1920, add animated captions and an opening hook, combine the overlay, and export H.264 MP4.
7. Copies the MP4 and review metadata into Google Drive / MyDrive / ReelFactory / output.

This does not promise that a clip will go viral. It is a repeatable selection and editing pipeline; performance still depends on the source, story, packaging, audience, and distribution.

## Architecture

- Gemini 3.8 Flash ranks moments and writes a concise hook/title. It is not trusted to invent timestamps.
- faster-whisper supplies the timing backbone for cuts and captions.
- Remotion owns the final 9:16 composition, timeline, captions, video layers, audio, and MP4 export.
- HyperFrames owns a separate HTML/CSS/JavaScript motion-graphics scene, using GSAP and Three.js for animated 2D/3D visual layers.
- Three.js is the 3D engine for every custom 3D shot. There is no Blender dependency or Blender rendering stage.
- Google Colab + Drive provide the execution environment and persistent input/output storage.

HyperFrames is not a native Remotion plugin. The current integration renders a transparent WebM overlay in HyperFrames and composites it in Remotion. Future editing plans may use Remotion-native compositions for some graphics and HyperFrames scenes for others, but Remotion remains the final timeline compositor and export engine.

## Start in Google Colab

Open the notebook:

https://colab.research.google.com/github/martyroy6996-spec/remotion-shorts-engine/blob/main/colab/Reel_Factory.ipynb

Recommended runtime: T4 GPU. The notebook installs Node.js 22, FFmpeg, Python requirements, Remotion, and HyperFrames, then checks the installed versions.

### First-time setup

1. Open the notebook in Colab and connect a runtime.
2. In Colab, open Secrets (key icon) and add GEMINI_API_KEY. Grant notebook access to the secret. The notebook also supports a one-session hidden prompt if you do not use Colab Secrets.
3. Mount Google Drive when prompted.
4. Upload one or more source videos to MyDrive/ReelFactory/input.
5. Run the analysis cell. Review the clip candidates and their scores.
6. Enter the candidate number(s) you want to render. The top-ranked candidate is index 0.
7. Find the finished MP4 in MyDrive/ReelFactory/output.

The notebook clones the current code from this public repository into the Colab runtime. Your Drive videos are not uploaded to GitHub.

## Drive folders

- MyDrive/ReelFactory/input/ — source podcast/interview/clipping videos.
- MyDrive/ReelFactory/output/ — rendered MP4s, transcript, candidate list, and render manifest.

## Run locally

Requirements: Node.js 22+, FFmpeg, Python 3.10+, and a Gemini API key.

    npm install
    python -m pip install -r requirements.txt
    export GEMINI_API_KEY="YOUR_KEY"
    python pipeline/clipper.py analyze --input "/path/to/podcast.mp4" --workdir "/path/to/reel-work"
    python pipeline/clipper.py render --input "/path/to/podcast.mp4" --workdir "/path/to/reel-work" --candidate-index 0 --drive-output "/path/to/output"

The render step runs hyperframes lint, renders the WebM overlay, then calls the Remotion CLI.

## Important constraints

- Keep the repository free of real API keys. Colab Secrets is the preferred key store.
- Source footage is copied into the ephemeral Colab runtime during rendering and is not committed.
- The first version uses one fixed Three.js 3D overlay system and a configurable center crop. More advanced layouts, speaker-aware reframing, B-roll search, multi-speaker cuts, SFX, story-specific Three.js scenes, and style presets are next-stage work.
- Whisper GPU inference may fall back to CPU if the Colab CUDA/CTranslate2 stack is incompatible. CPU fallback works but is slower.
- HyperFrames and Remotion render inside the Colab runtime. A notebook run is required before any MP4 can appear in Drive.

## Licensing

Remotion's current terms allow free use for individuals and organizations with up to three employees, including commercial video creation, subject to its terms. Larger organizations may need a company license. Check the official Remotion license page before production use: https://www.remotion.dev/docs/license/pricing

## Upstream references

- Remotion documentation: https://www.remotion.dev/docs/
- Remotion rendering: https://www.remotion.dev/docs/render
- HyperFrames CLI: https://hyperframes.app/docs/
- Gemini video understanding: https://ai.google.dev/gemini-api/docs/video-understanding
- Google GenAI SDK: https://ai.google.dev/gemini-api/docs/migrate
