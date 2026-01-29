type MermaidType = typeof import("mermaid").default;

let mermaidInstance: MermaidType | null = null;
let initializing: Promise<MermaidType> | null = null;

export async function getMermaid(): Promise<MermaidType> {
  if (mermaidInstance !== null) return mermaidInstance;
  if (initializing !== null) return initializing;

  initializing = (async () => {
    const { default: mermaid } = await import("mermaid");

    mermaid.initialize({
      startOnLoad: false,
      theme: "default",
      securityLevel: "antiscript",
      fontFamily: "ui-sans-serif, system-ui, sans-serif",
    });

    mermaidInstance = mermaid;
    initializing = null;
    return mermaid;
  })();

  return initializing;
}

// Deprecated: No longer needed with lazy loading
export function initMermaid() {
  // Logic moved to getMermaid
}

export function isMermaidInitialized() {
  return mermaidInstance !== null;
}
