import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App.tsx";
import "./index.css";
import { initMermaid } from "./utils/mermaidConfig";

// Initialize mermaid once at app startup
initMermaid();

const rootElement = document.getElementById("root");

if (rootElement === null) {
  throw new Error("Failed to find root element");
}

createRoot(rootElement).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
