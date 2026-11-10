import React from "react";
import { Composition } from "remotion";
import { ViralReel, type ReelProps } from "./Reel";

const defaultProps: ReelProps = {
  sourceFile: "source.mp4",
  overlayFile: "overlay.webm",
  sourceStartSec: 0,
  durationInSeconds: 30,
  headline: "THE MOMENT THAT CHANGES EVERYTHING",
  captions: [],
  focalX: 50,
  focalY: 50,
  audioVolume: 1
};

export const Root: React.FC = () => (
  <Composition
    id="ViralReel"
    component={ViralReel}
    width={1080}
    height={1920}
    fps={30}
    durationInFrames={900}
    defaultProps={defaultProps}
    calculateMetadata={({ props }) => ({
      durationInFrames: Math.max(1, Math.ceil(props.durationInSeconds * 30))
    })}
  />
);
