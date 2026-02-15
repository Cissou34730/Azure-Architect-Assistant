interface BaseCardProps {
  readonly title: string;
  readonly date: string;
  readonly onClick: () => void;
  readonly children?: React.ReactNode;
}

export function BaseCard({ title, date, onClick, children }: BaseCardProps) {
  return (
    <button
      onClick={onClick}
      className="w-full text-left p-2.5 rounded-lg border border-border hover:border-brand-line hover:bg-brand-soft/30 transition-all group"
    >
      <div className="flex justify-between items-start mb-1">
        <h4 className="text-sm font-medium text-foreground line-clamp-1 group-hover:text-brand-strong">
          {title}
        </h4>
      </div>
      <div className="flex items-center justify-between text-[11px] text-dim">
        <span>{date}</span>
      </div>
      {children !== undefined && children !== null && <div className="mt-2 text-xs text-secondary">{children}</div>}
    </button>
  );
}

