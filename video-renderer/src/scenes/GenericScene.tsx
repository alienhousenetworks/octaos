import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig, spring, interpolate } from "remotion";
import { Scene } from "../types";
import { AnimatedText } from "../components/AnimatedText";
import { AnimatedAsset } from "../components/AnimatedAsset";

export const GenericScene: React.FC<{
  scene: Scene;
}> = ({ scene }) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();

  // Background fade in
  const bgOpacity = interpolate(frame, [0, 15], [0, 1], {
    extrapolateRight: "clamp",
  });

  // Fade out at the end of the scene
  const fadeOutStart = durationInFrames - 15;
  const masterOpacity = interpolate(frame, [fadeOutStart, durationInFrames], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Decide alignment based on scene type
  const isLogo = scene.type === "LogoReveal";
  const isDashboard = scene.type === "DashboardScene";

  return (
    <AbsoluteFill
      style={{
        backgroundColor: "#0a0a0a",
        opacity: masterOpacity,
        fontFamily: "'Inter', sans-serif",
        color: "white",
        display: "flex",
        flexDirection: isDashboard ? "row" : "column",
        alignItems: "center",
        justifyContent: "center",
        padding: "4rem",
        overflow: "hidden",
      }}
    >
      {/* Background layer (3d_environment) */}
      {scene.assets?.filter(a => a.type === "3d_environment").map((asset, idx) => (
        <AnimatedAsset key={`bg-${idx}`} asset={asset} index={0} />
      ))}

      {/* Main Content Area */}
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: isLogo ? "center" : "flex-start",
          justifyContent: "center",
          flex: isDashboard ? 1 : "none",
          zIndex: 10,
          textAlign: isLogo ? "center" : "left",
          width: isLogo ? "100%" : "auto",
        }}
      >
        {scene.headline && (
          <AnimatedText
            text={scene.headline}
            delay={0}
            style={{
              fontSize: isLogo ? "80px" : "64px",
              fontWeight: 800,
              background: "linear-gradient(90deg, #fff, #a8a8ff)",
              WebkitBackgroundClip: "text",
              WebkitTextFillColor: "transparent",
              marginBottom: "1rem",
            }}
          />
        )}
        
        {scene.subheadline && (
          <AnimatedText
            text={scene.subheadline}
            delay={10}
            style={{
              fontSize: isLogo ? "40px" : "32px",
              fontWeight: 400,
              color: "#aaa",
              marginBottom: "3rem",
            }}
          />
        )}

        {isLogo && scene.assets?.find(a => a.type === "logo") && (
          <div style={{ marginTop: "4rem" }}>
            <AnimatedAsset 
              asset={scene.assets.find(a => a.type === "logo")!} 
              index={2} 
            />
          </div>
        )}
      </div>

      {/* Assets Grid */}
      {!isLogo && (
        <div
          style={{
            display: "flex",
            flexWrap: "wrap",
            gap: "2rem",
            justifyContent: isDashboard ? "center" : "flex-start",
            flex: isDashboard ? 2 : "none",
            zIndex: 10,
            marginTop: isDashboard ? 0 : "2rem",
          }}
        >
          {scene.assets
            ?.filter(a => a.type !== "3d_environment" && a.type !== "logo")
            .map((asset, idx) => (
              <AnimatedAsset key={idx} asset={asset} index={idx + 3} />
            ))}
        </div>
      )}
    </AbsoluteFill>
  );
};
