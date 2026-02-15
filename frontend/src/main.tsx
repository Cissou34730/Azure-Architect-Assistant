import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App.tsx";
import "./index.css";
import { initMermaid } from "./utils/mermaidConfig";
import { initializeTheme } from "./hooks/useTheme";

// Initialize mermaid once at app startup
initMermaid();
initializeTheme();

const rootElement = document.getElementById("root");

if (rootElement === null) {
  throw new Error("Failed to find root element");
}

createRoot(rootElement).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
