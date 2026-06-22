import React from "react";
import { Composition, Series, Audio, AbsoluteFill, useVideoConfig } from "remotion";
import { Blueprint } from "./types";
import { GenericScene } from "./scenes/GenericScene";

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="VideoBlueprint"
        component={VideoBlueprintComponent}
        // Duration will be dynamically determined, but we need a fallback/initial value for Remotion root
        durationInFrames={30 * 30} 
        fps={30}
        width={1920}
        height={1080}
        defaultProps={{ 
          blueprint: {
            version: "1.0",
            title: "Fallback",
            duration: 30,
            aspect_ratio: "16:9",
            scenes: []
          } as Blueprint
        }}
        calculateMetadata={({ props }) => {
          // Calculate exact total duration in frames based on scenes
          const fps = 30;
          let totalDurationInFrames = 0;
          
          if (props.blueprint && props.blueprint.scenes) {
            totalDurationInFrames = props.blueprint.scenes.reduce(
              (acc, scene) => acc + (scene.duration || 5) * fps, 
              0
            );
          }
          
          return {
            durationInFrames: totalDurationInFrames > 0 ? totalDurationInFrames : 30 * fps,
            props,
          };
        }}
      />
    </>
  );
};

const VideoBlueprintComponent: React.FC<{ blueprint: Blueprint }> = ({ blueprint }) => {
  const { fps } = useVideoConfig();

  if (!blueprint || !blueprint.scenes || blueprint.scenes.length === 0) {
    return (
      <div style={{ flex: 1, backgroundColor: "black", color: "white", display: "flex", alignItems: "center", justifyContent: "center" }}>
        <h1>No scenes found in blueprint.</h1>
      </div>
    );
  }

  // A free cinematic ambient track for background music
  // In production, this can be dynamically provided by an AI Music Generator like Suno via the blueprint
  const BGM_URL = "https://actions.google.com/sounds/v1/science_fiction/alien_spaceship_ambience.ogg";

  return (
    <AbsoluteFill>
      {/* Background Music */}
      <Audio 
        src={blueprint.voiceover || BGM_URL} 
        volume={0.3} 
        loop 
      />

      {/* Optional Voiceover Track - if it's explicitly provided */}
      {blueprint.voiceover && blueprint.voiceover.startsWith("http") && (
        <Audio 
          src={blueprint.voiceover} 
          volume={0.8} 
        />
      )}

      <Series>
        {blueprint.scenes.map((scene, idx) => {
          const sceneDurationInFrames = (scene.duration || 5) * fps;
          
          return (
            <Series.Sequence key={scene.id || `scene-${idx}`} durationInFrames={sceneDurationInFrames}>
              <GenericScene scene={scene} />
              
              {/* Scene-specific Voiceover / Audio */}
              {scene.voiceover_segment && scene.voiceover_segment.startsWith("http") && (
                <Audio 
                  src={scene.voiceover_segment} 
                  volume={0.8} 
                />
              )}
            </Series.Sequence>
          );
        })}
      </Series>
    </AbsoluteFill>
  );
};
