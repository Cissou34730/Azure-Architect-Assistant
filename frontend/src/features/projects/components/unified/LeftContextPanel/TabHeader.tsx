import { Badge } from "../../../../../components/common/Badge";

export type TabType = "requirements" | "assumptions" | "questions" | "documents";

export interface TabItem {
  readonly id: TabType;
  readonly label: string;
  readonly icon: React.ElementType;
  readonly count: number;
}

interface TabHeaderProps {
  readonly tabs: readonly TabItem[];
  readonly activeTab: TabType;
  readonly onTabChange: (id: TabType) => void;
}

export function TabHeader({ tabs, activeTab, onTabChange }: TabHeaderProps) {
  return (
    <div className="flex border-b border-gray-200 bg-white shrink-0">
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
      className={`flex-1 flex flex-col items-center gap-1 py-3 px-2 text-xs font-medium transition-colors border-b-2 ${
        isActive
          ? "text-blue-600 border-blue-600 bg-blue-50"
          : "text-gray-600 border-transparent hover:text-gray-900 hover:bg-gray-50"
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

