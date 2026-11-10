import React from "react";
import {
  AbsoluteFill,
  OffthreadVideo,
  Sequence,
  Video,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig
} from "remotion";

export type CaptionItem = {
  text: string;
  start: number;
  end: number;
  emphasis?: boolean;
};

export type ReelProps = {
  sourceFile: string;
  overlayFile: string;
  sourceStartSec: number;
  durationInSeconds: number;
  headline: string;
  captions: CaptionItem[];
  focalX: number;
  focalY: number;
  audioVolume: number;
};

const CaptionLine: React.FC<{ caption: CaptionItem }> = ({ caption }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const pop = spring({
    frame,
    fps,
    config: { damping: 16, mass: 0.55, stiffness: 150 }
  });
  const captionDurationFrames = Math.max(1, Math.ceil((caption.end - caption.start) * fps));
  const fadeStartFrame = Math.max(5, captionDurationFrames - 5);
  const fadeOut = interpolate(
    frame,
    [0, 5, fadeStartFrame, captionDurationFrames],
    [0, 1, 1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  return (
    <AbsoluteFill
      style={{
        justifyContent: "flex-end",
        alignItems: "center",
        paddingLeft: 64,
        paddingRight: 64,
        paddingBottom: 365,
        pointerEvents: "none"
      }}
    >
      <div
        style={{
          transform: "scale(" + (0.92 + pop * 0.08) + ")",
          opacity: fadeOut,
          maxWidth: 960,
          padding: "14px 22px 17px",
          borderRadius: 18,
          background: "rgba(4, 7, 13, 0.72)",
          border: "1px solid rgba(255,255,255,0.16)",
          color: caption.emphasis ? "#FFE36B" : "#FFFFFF",
          fontFamily: "Arial, Helvetica, sans-serif",
          fontSize: caption.text.length > 25 ? 58 : 72,
          fontWeight: 900,
          lineHeight: 1.08,
          letterSpacing: "-1.9px",
          textAlign: "center",
          textTransform: "uppercase",
          textShadow: "0 4px 18px rgba(0,0,0,0.9)",
          boxShadow: "0 10px 44px rgba(0,0,0,0.24)"
        }}
      >
        {caption.text}
      </div>
    </AbsoluteFill>
  );
};

const HookTitle: React.FC<{ text: string }> = ({ text }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const entrance = spring({
    frame,
    fps,
    config: { damping: 17, mass: 0.65, stiffness: 120 }
  });
  const opacity = interpolate(frame, [0, 8, 55, 72], [0, 1, 1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp"
  });

  return (
    <AbsoluteFill
      style={{
        justifyContent: "flex-start",
        alignItems: "center",
        paddingTop: 245,
        paddingLeft: 72,
        paddingRight: 72,
        pointerEvents: "none"
      }}
    >
      <div
        style={{
          maxWidth: 920,
          opacity,
          transform: "translateY(" + ((1 - entrance) * 42) + "px)",
          color: "#FFFFFF",
          fontFamily: "Arial, Helvetica, sans-serif",
          fontSize: 66,
          lineHeight: 0.98,
          fontWeight: 950,
          letterSpacing: "-2.5px",
          textAlign: "center",
          textTransform: "uppercase",
          textShadow: "0 5px 26px rgba(0,0,0,0.9)"
        }}
      >
        {text}
      </div>
      <div
        style={{
          marginTop: 24,
          width: 118,
          height: 8,
          borderRadius: 20,
          background: "linear-gradient(90deg, #55D6FF, #F6C85F)",
          opacity
        }}
      />
    </AbsoluteFill>
  );
};

export const ViralReel: React.FC<ReelProps> = (props) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const progress = interpolate(frame, [0, durationInFrames], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp"
  });
  const startFrame = Math.max(0, Math.round(props.sourceStartSec * fps));
  const endFrame = Math.max(startFrame + 1, Math.round((props.sourceStartSec + props.durationInSeconds) * fps));

  return (
    <AbsoluteFill style={{ backgroundColor: "#05070C" }}>
      <OffthreadVideo
        src={staticFile(props.sourceFile)}
        startFrom={startFrame}
        endAt={endFrame}
        volume={props.audioVolume}
        style={{
          width: "100%",
          height: "100%",
          objectFit: "cover",
          objectPosition: props.focalX + "% " + props.focalY + "%"
        }}
      />

      <AbsoluteFill
        style={{
          background: "linear-gradient(180deg, rgba(0,0,0,0.26) 0%, transparent 28%, transparent 56%, rgba(0,0,0,0.30) 100%)"
        }}
      />

      <Video
        src={staticFile(props.overlayFile)}
        muted
        startFrom={0}
        endAt={Math.max(1, Math.ceil(props.durationInSeconds * fps))}
        style={{ width: "100%", height: "100%", objectFit: "cover" }}
      />

      <Sequence from={0} durationInFrames={Math.min(82, durationInFrames)}>
        <HookTitle text={props.headline} />
      </Sequence>

      {props.captions.map((caption, index) => {
        const from = Math.max(0, Math.floor(caption.start * fps));
        const duration = Math.max(1, Math.ceil((caption.end - caption.start) * fps));
        return (
          <Sequence key={index} from={from} durationInFrames={duration}>
            <CaptionLine caption={caption} />
          </Sequence>
        );
      })}

      <AbsoluteFill style={{ justifyContent: "flex-start", pointerEvents: "none" }}>
        <div style={{ height: 8, width: "100%", background: "rgba(255,255,255,0.20)" }}>
          <div
            style={{
              height: "100%",
              width: (progress * 100) + "%",
              background: "linear-gradient(90deg, #4FD8FF, #FFE36B)"
            }}
          />
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
