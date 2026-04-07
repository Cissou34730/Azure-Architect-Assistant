import { useRef, useEffect } from "react";

interface KBItemDropdownProps {
  readonly showActions: boolean;
  readonly setShowActions: (show: boolean) => void;
  readonly onDelete: () => void;
}

export function KBItemDropdown({
  showActions,
  setShowActions,
  onDelete,
}: KBItemDropdownProps) {
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        dropdownRef.current !== null &&
        event.target instanceof Node &&
        !dropdownRef.current.contains(event.target)
      ) {
        setShowActions(false);
      }
    };

    if (showActions) {
      document.addEventListener("mousedown", handleClickOutside);
      return () => {
        document.removeEventListener("mousedown", handleClickOutside);
      };
    }
    return undefined;
  }, [showActions, setShowActions]);

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => {
          setShowActions(!showActions);
        }}
        onKeyDown={(e) => {
          if (e.key === "Escape") {
            setShowActions(false);
          }
        }}
        className="px-2 py-1.5 text-sm text-secondary hover:bg-muted rounded-button"
        aria-label="More actions"
        aria-expanded={showActions ? "true" : "false"}
        aria-haspopup="menu"
      >
        <svg
          className="w-5 h-5"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M12 5v.01M12 12v.01M12 19v.01M12 6a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2z"
          />
        </svg>
      </button>

      {showActions && (
        <div
          className="absolute right-0 mt-1 w-48 bg-card rounded-button shadow-lg border border-border z-20"
          role="menu"
        >
          <button
            onClick={() => {
              setShowActions(false);
              onDelete();
            }}
            className="w-full px-4 py-2 text-left text-sm text-danger hover:bg-danger-soft rounded-button"
            role="menuitem"
          >
            Delete Knowledge Base
          </button>
        </div>
      )}
    </div>
  );
}


