import { createElement, type ReactNode } from "react";
import type { LucideIcon } from "lucide-react";
import { Badge } from "../../../../../components/common/Badge";

interface SectionHeaderProps {
  readonly title: string;
  readonly count: number;
}

export function SectionHeader({ title, count }: SectionHeaderProps) {
  return (
    <div className="flex items-center justify-between text-xs font-semibold uppercase tracking-wider text-gray-500">
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
    color === "emerald" ? "text-emerald-700 bg-emerald-50" : "text-blue-700 bg-blue-50";
  return (
    <button
      type="button"
      onClick={onClick}
      className="w-full flex items-center gap-2 rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
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
    <div className="rounded-lg border border-gray-200 bg-white">
      <div className="px-3 py-2 text-xs font-semibold uppercase tracking-wide text-gray-500 border-b border-gray-100">
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
      className="w-full flex items-center gap-2 rounded-md px-2 py-1.5 text-sm text-gray-700 hover:bg-gray-50"
    >
      {createElement(iconComponent, { className: "h-4 w-4 text-gray-500" })}
      <span className="truncate">{label}</span>
    </button>
  );
}

export function EmptyRow({ text }: { readonly text: string }) {
  return <div className="text-xs text-gray-500 px-2 py-1">{text}</div>;
}
