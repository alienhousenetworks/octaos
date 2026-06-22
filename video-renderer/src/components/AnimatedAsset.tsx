import React from "react";
import { spring, interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { Asset } from "../types";

export const AnimatedAsset: React.FC<{
  asset: Asset;
  index: number;
}> = ({ asset, index }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const delay = index * 10 + 15; // stagger appearance

  // Basic enter animation
  const appear = spring({
    frame: frame - delay,
    fps,
    config: {
      damping: 12,
    },
  });

  // Continuous subtle pulse/float
  const float = Math.sin(frame / 30) * 10;

  const scale = interpolate(appear, [0, 1], [0.8, 1]);
  const opacity = interpolate(appear, [0, 1], [0, 1]);

  // Styling maps based on asset type
  const getStyleForType = (type: string): React.CSSProperties => {
    switch (type) {
      case "3d_environment":
        return {
          position: "absolute",
          top: 0,
          left: 0,
          width: "100%",
          height: "100%",
          background: "linear-gradient(135deg, #110022 0%, #000000 100%)",
          opacity: 0.8,
          zIndex: -1,
        };
      case "vfx":
        return {
          padding: "1rem",
          borderRadius: "8px",
          backgroundColor: "rgba(100, 50, 255, 0.2)",
          border: "1px solid rgba(150, 100, 255, 0.4)",
          boxShadow: "0 0 20px rgba(100, 50, 255, 0.2)",
        };
      case "ui_element":
        return {
          padding: "1.5rem",
          borderRadius: "16px",
          backgroundColor: "rgba(255, 255, 255, 0.1)",
          backdropFilter: "blur(10px)",
          border: "1px solid rgba(255, 255, 255, 0.2)",
        };
      default:
        return {
          padding: "1rem",
          backgroundColor: "rgba(40, 40, 40, 0.5)",
          borderRadius: "8px",
        };
    }
  };

  const style = getStyleForType(asset.type);

  if (asset.type === "3d_environment") {
    // Fill background
    return <div style={{ ...style, opacity: opacity * 0.8 }} />;
  }

  return (
    <div
      style={{
        ...style,
        opacity,
        transform: `scale(${scale}) translateY(${float}px)`,
        display: "flex",
        flexDirection: "column",
        gap: "0.5rem",
        minWidth: "200px",
        maxWidth: "300px",
      }}
    >
      <div style={{ fontSize: "12px", textTransform: "uppercase", letterSpacing: "2px", color: "#a88" }}>
        {asset.type.replace("_", " ")}
      </div>
      <div style={{ fontWeight: "bold", fontSize: "18px", color: "white" }}>
        {asset.name}
      </div>
      <div style={{ fontSize: "14px", color: "#ccc" }}>
        {asset.description}
      </div>
    </div>
  );
};
