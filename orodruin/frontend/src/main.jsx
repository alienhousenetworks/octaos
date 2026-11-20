import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import OctaOSApp from "./OctaOSApp.jsx";

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <OctaOSApp />
  </StrictMode>
);
