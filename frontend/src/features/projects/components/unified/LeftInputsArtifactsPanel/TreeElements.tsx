import { createElement, type ReactNode } from "react";
import type { LucideIcon } from "lucide-react";
import { Badge } from "../../../../../components/common/Badge";

interface SectionHeaderProps {
  readonly title: string;
  readonly count: number;
}

export function SectionHeader({ title, count }: SectionHeaderProps) {
  return (
    <div className="flex items-center justify-between text-xs font-semibold uppercase tracking-wider text-dim">
      <span>{title}</span>
      <Badge size="sm" variant="default">{count}</Badge>
    </div>
  );
}

interface TreeButtonProps {
  readonly icon: LucideIcon;
  readonly label: string;
  readonly badge: number;
  readonly color: "emerald" | "blue";
  readonly onClick: () => void;
}

export function TreeButton({ icon, label, badge, color, onClick }: TreeButtonProps) {
  const iconComponent = icon;
  const colorClasses =
    color === "emerald" ? "text-info-strong bg-info-soft" : "text-brand-strong bg-brand-soft";
  return (
    <button
      type="button"
      onClick={onClick}
      className="w-full flex items-center gap-2 rounded-lg border border-border bg-card px-3 py-2 text-sm font-medium text-secondary hover:bg-surface transition-colors"
    >
      <span className={`h-8 w-8 rounded-md flex items-center justify-center ${colorClasses}`}>
        {createElement(iconComponent, { className: "h-4 w-4" })}
      </span>
      <span className="flex-1 text-left truncate">{label}</span>
      <Badge size="sm" variant={color === "emerald" ? "success" : "primary"}>
        {badge}
      </Badge>
    </button>
  );
}

interface TreeGroupProps {
  readonly label: string;
  readonly children: ReactNode;
}

export function TreeGroup({ label, children }: TreeGroupProps) {
  return (
    <div className="rounded-lg border border-border bg-card">
      <div className="px-3 py-2 text-xs font-semibold uppercase tracking-wide text-dim border-b border-border">
        {label}
      </div>
      <div className="p-2 space-y-2">{children}</div>
    </div>
  );
}

interface TreeRowProps {
  readonly icon: LucideIcon;
  readonly label: string;
  readonly onClick: () => void;
}

export function TreeRow({ icon, label, onClick }: TreeRowProps) {
  const iconComponent = icon;
  return (
    <button
      type="button"
      onClick={onClick}
      className="w-full flex items-center gap-2 rounded-md px-2 py-1.5 text-sm text-secondary hover:bg-surface"
    >
      {createElement(iconComponent, { className: "h-4 w-4 text-dim" })}
      <span className="truncate">{label}</span>
    </button>
  );
}

export function EmptyRow({ text }: { readonly text: string }) {
  return <div className="text-xs text-dim px-2 py-1">{text}</div>;
}


