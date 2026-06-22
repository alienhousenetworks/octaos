import React from "react";
import { Composition } from "remotion";

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="VideoBlueprint"
        component={VideoBlueprintComponent}
        durationInFrames={30 * 30} // default 30 secs
        fps={30}
        width={1920}
        height={1080}
        defaultProps={{ blueprint: {} }}
      />
    </>
  );
};

const VideoBlueprintComponent: React.FC<{ blueprint: any }> = ({ blueprint }) => {
  return (
    <div style={{ flex: 1, backgroundColor: "black", color: "white", display: "flex", alignItems: "center", justifyContent: "center" }}>
      <h1>{blueprint?.title || "Video Blueprint"}</h1>
    </div>
  );
};
