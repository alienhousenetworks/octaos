import express from "express";
import cors from "cors";
import asyncHandler from "express-async-handler";
import { bundle } from "@remotion/bundler";
import { renderMedia, selectComposition } from "@remotion/renderer";
import path from "path";
import dotenv from "dotenv";
import fs from "fs";

dotenv.config();

const app = express();
app.use(cors());
app.use(express.json({ limit: "50mb" }));

const COMPOSITION_ID = "VideoBlueprint";
const ENTRY_POINT = path.resolve(__dirname, "src/index.ts");
const OUT_DIR = path.resolve(__dirname, "out");

if (!fs.existsSync(OUT_DIR)) {
  fs.mkdirSync(OUT_DIR, { recursive: true });
}

app.post(
  "/render",
  asyncHandler(async (req, res) => {
    const blueprint = req.body;
    
    if (!blueprint || !blueprint.scenes) {
      res.status(400).json({ error: "Invalid Video Blueprint JSON" });
      return;
    }

    console.log("Bundling Remotion project...");
    const bundled = await bundle({
      entryPoint: ENTRY_POINT,
      webpackOverride: (config) => config,
    });

    console.log("Extracting composition...");
    const composition = await selectComposition({
      serveUrl: bundled,
      id: COMPOSITION_ID,
      inputProps: { blueprint },
    });

    const outputLocation = path.resolve(OUT_DIR, `render-${Date.now()}.mp4`);
    console.log(`Rendering to ${outputLocation}...`);

    await renderMedia({
      composition,
      serveUrl: bundled,
      codec: "h264",
      outputLocation,
      inputProps: { blueprint },
      onProgress: ({ progress }) => {
        console.log(`Rendering is ${Math.round(progress * 100)}% complete`);
      },
    });

    res.json({ status: "success", file: outputLocation });
  })
);

const PORT = process.env.PORT || 8002;
app.listen(PORT, () => {
  console.log(`Video Renderer API running on port ${PORT}`);
});
