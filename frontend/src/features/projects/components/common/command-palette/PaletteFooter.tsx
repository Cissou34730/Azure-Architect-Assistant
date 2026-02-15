export function PaletteFooter() {
  return (
    <div className="px-4 py-2 border-t border-border bg-surface flex items-center justify-between text-xs text-dim">
      <div className="flex gap-4">
        <span>
          <kbd className="bg-card border rounded px-1 mr-1">↑↓</kbd> to navigate
        </span>
        <span>
          <kbd className="bg-card border rounded px-1 mr-1">Enter</kbd> to select
        </span>
      </div>
      <span>
        <kbd className="bg-card border rounded px-1 mr-1">Esc</kbd> to close
      </span>
    </div>
  );
}

