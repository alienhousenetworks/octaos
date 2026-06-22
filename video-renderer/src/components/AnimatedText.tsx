import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";

export const AnimatedText: React.FC<{
  text: string;
  delay?: number;
  style?: React.CSSProperties;
  className?: string;
}> = ({ text, delay = 0, style, className }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const animationProgress = spring({
    frame: frame - delay,
    fps,
    config: {
      damping: 200,
    },
  });

  const translateY = interpolate(animationProgress, [0, 1], [50, 0]);
  const opacity = interpolate(animationProgress, [0, 1], [0, 1]);

  return (
    <div
      style={{
        opacity,
        transform: `translateY(${translateY}px)`,
        ...style,
      }}
      className={className}
    >
      {text}
    </div>
  );
};
