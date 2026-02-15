import { Badge } from "../../../../../components/common/Badge";

export type TabType = "requirements" | "assumptions" | "questions" | "documents";

export interface TabItem {
  readonly id: TabType;
  readonly label: string;
  readonly icon: React.ElementType;
  readonly count: number;
  readonly tooltip?: string;
}

interface TabHeaderProps {
  readonly tabs: readonly TabItem[];
  readonly activeTab: TabType;
  readonly onTabChange: (id: TabType) => void;
}

export function TabHeader({ tabs, activeTab, onTabChange }: TabHeaderProps) {
  return (
    <div className="flex border-b border-border bg-card shrink-0">
      {tabs.map((tab) => (
        <TabButton
          key={tab.id}
          tab={tab}
          isActive={activeTab === tab.id}
          onClick={() => { onTabChange(tab.id); }}
        />
      ))}
    </div>
  );
}

interface TabButtonProps {
  readonly tab: TabItem;
  readonly isActive: boolean;
  readonly onClick: () => void;
}

function TabButton({ tab, isActive, onClick }: TabButtonProps) {
  const Icon = tab.icon; // eslint-disable-line @typescript-eslint/naming-convention
  return (
    <button
      onClick={onClick}
      title={tab.tooltip}
      className={`flex-1 flex flex-col items-center gap-1 py-3 px-2 text-xs font-medium transition-colors border-b-2 ${
        isActive
          ? "text-brand border-brand bg-brand-soft"
          : "text-secondary border-transparent hover:text-foreground hover:bg-surface"
      }`}
      type="button"
    >
      <div className="flex items-center gap-1">
        <Icon className="h-4 w-4" />
        {tab.count > 0 && (
          <Badge size="sm">
            {tab.count}
          </Badge>
        )}
      </div>
      <span className="hidden lg:inline">{tab.label}</span>
    </button>
  );
}


