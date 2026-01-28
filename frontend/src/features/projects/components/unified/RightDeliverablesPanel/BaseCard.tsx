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
      className="w-full text-left p-2.5 rounded-lg border border-gray-100 hover:border-blue-200 hover:bg-blue-50/30 transition-all group"
    >
      <div className="flex justify-between items-start mb-1">
        <h4 className="text-sm font-medium text-gray-900 line-clamp-1 group-hover:text-blue-700">
          {title}
        </h4>
      </div>
      <div className="flex items-center justify-between text-[11px] text-gray-500">
        <span>{date}</span>
      </div>
      {children !== undefined && children !== null && <div className="mt-2 text-xs text-gray-600">{children}</div>}
    </button>
  );
}
