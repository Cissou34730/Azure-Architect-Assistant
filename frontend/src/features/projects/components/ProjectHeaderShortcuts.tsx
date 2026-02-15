
export interface KeyboardShortcut {
  key: string;
  label: string;
  action: () => void;
  visible?: boolean;
}

interface ProjectHeaderShortcutsProps {
  shortcuts: KeyboardShortcut[];
}

export function ProjectHeaderShortcuts({ shortcuts }: ProjectHeaderShortcutsProps) {
  return (
    <div className="mt-3 p-3 bg-card rounded-lg border border-border shadow-md animate-in fade-in slide-in-from-top-2 duration-200">
      <h3 className="text-xs font-semibold text-secondary mb-2">Keyboard Shortcuts</h3>
      <div className="grid grid-cols-2 gap-2">
        {shortcuts.map((shortcut) => (
          <div key={shortcut.key} className="flex items-center justify-between text-xs">
            <span className="text-secondary">{shortcut.label}</span>
            <kbd className="px-2 py-1 bg-muted border border-border-stronger rounded text-secondary font-mono">
              {shortcut.key}
            </kbd>
          </div>
        ))}
      </div>
    </div>
  );
}

