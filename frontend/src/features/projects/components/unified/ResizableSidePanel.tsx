import { useCallback, type ReactNode } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";

interface ResizableSidePanelProps {
  readonly side: "left" | "right";
  readonly isOpen: boolean;
  readonly width: number;
  readonly minWidth: number;
  readonly maxWidth: number;
  readonly onResize: (width: number) => void;
  readonly onToggle: () => void;
  readonly collapsedTitle: string;
  readonly children: ReactNode;
  readonly className?: string;
}

interface NextWidthParams {
  readonly side: "left" | "right";
  readonly clientX: number;
  readonly minWidth: number;
  readonly maxWidth: number;
}

function getNextWidth({ side, clientX, minWidth, maxWidth }: NextWidthParams): number {
  const viewportWidth = window.innerWidth;
  const rawWidth = side === "left" ? clientX : viewportWidth - clientX;
  return Math.max(minWidth, Math.min(maxWidth, rawWidth));
}

export function ResizableSidePanel({
  side,
  isOpen,
  width,
  minWidth,
  maxWidth,
  onResize,
  onToggle,
  collapsedTitle,
  children,
  className = "",
}: ResizableSidePanelProps) {
  const handlePointerDown = useCallback(
    (event: React.PointerEvent<HTMLDivElement>) => {
      event.preventDefault();
      const target = event.currentTarget;
      target.setPointerCapture(event.pointerId);

      const handlePointerMove = (moveEvent: PointerEvent) => {
        onResize(getNextWidth({ side, clientX: moveEvent.clientX, minWidth, maxWidth }));
      };

      const handlePointerUp = () => {
        target.releasePointerCapture(event.pointerId);
        window.removeEventListener("pointermove", handlePointerMove);
        window.removeEventListener("pointerup", handlePointerUp);
      };

      window.addEventListener("pointermove", handlePointerMove);
      window.addEventListener("pointerup", handlePointerUp);
    },
    [side, minWidth, maxWidth, onResize],
  );

  if (!isOpen) {
    const collapsedClasses =
      side === "left"
        ? "left-0 border-r rounded-r-lg"
        : "right-0 border-l rounded-l-lg";
    return (
      <button
        onClick={onToggle}
        className={`fixed ${collapsedClasses} top-1/2 -translate-y-1/2 bg-card border border-border p-2 shadow-lg hover:bg-surface transition-colors z-20`}
        title={collapsedTitle}
        type="button"
      >
        {side === "left" ? (
          <ChevronRight className="h-5 w-5 text-secondary" />
        ) : (
          <ChevronLeft className="h-5 w-5 text-secondary" />
        )}
      </button>
    );
  }

  const handleClasses =
    side === "left"
      ? "absolute right-0 top-0 h-full w-2 cursor-col-resize z-20"
      : "absolute left-0 top-0 h-full w-2 cursor-col-resize z-20";

  return (
    <div
      className={`group panel-scroll-scope relative h-full bg-card ${side === "left" ? "border-r" : "border-l"} border-border ${className}`}
      style={{ width }}
    >
      <div
        role="separator"
        aria-orientation="vertical"
        onPointerDown={handlePointerDown}
        className={`${handleClasses} opacity-0 group-hover:opacity-100 group/handle`}
      >
        <div className="absolute inset-y-0 left-0 right-0 mx-auto w-0.5 bg-transparent transition-colors opacity-0 group-hover/handle:opacity-100 group-hover/handle:bg-brand" />
      </div>
      {children}
    </div>
  );
}


