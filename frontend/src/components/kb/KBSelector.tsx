import { Card } from "../common";

interface KB {
  readonly id: string;
  readonly name: string;
  readonly status: string;
  readonly profiles: readonly string[];
  readonly indexReady?: boolean;
}

interface Props {
  readonly availableKBs: readonly KB[];
  readonly selectedKBs: readonly string[];
  readonly onSelectionChange: (kbIds: string[]) => void;
  readonly disabled?: boolean;
}

interface KBItemProps {
  readonly kb: KB;
  readonly isSelected: boolean;
  readonly disabled?: boolean;
  readonly onToggle: (kbId: string) => void;
}

function KBItem({ kb, isSelected, disabled, onToggle }: KBItemProps) {
  const isActuallyDisabled =
    disabled === true || kb.status !== "active" || kb.indexReady === false;

  return (
    <label
      className={`flex items-center p-3 rounded-lg border cursor-pointer transition-colors ${
        isSelected
          ? "bg-brand-soft border-brand-line"
          : "bg-surface border-border hover:bg-muted"
      } ${
        disabled === true || kb.indexReady === false
          ? "opacity-50 cursor-not-allowed"
          : ""
      }`}
    >
      <input
        type="checkbox"
        checked={isSelected}
        onChange={() => {
          onToggle(kb.id);
        }}
        disabled={isActuallyDisabled}
        className="w-4 h-4 text-brand rounded focus:ring-brand"
      />
      <div className="ml-3 flex-1">
        <div className="flex items-center justify-between">
          <span className="font-medium text-foreground">{kb.name}</span>
          <span
            className={`text-xs px-2 py-1 rounded ${
              kb.status === "active" && kb.indexReady !== false
                ? "bg-success-soft text-success-strong"
                : "bg-warning-soft text-warning-strong"
            }`}
          >
            {kb.indexReady === false ? "not-indexed" : kb.status}
          </span>
        </div>
        {kb.profiles.length > 0 && (
          <div className="flex gap-1 mt-1">
            {kb.profiles.map((profile) => (
              <span
                key={profile}
                className="text-xs text-secondary bg-muted px-2 py-0.5 rounded"
              >
                {profile}
              </span>
            ))}
          </div>
        )}
      </div>
    </label>
  );
}

export function KBSelector({
  availableKBs,
  selectedKBs,
  onSelectionChange,
  disabled,
}: Props) {
  const handleToggle = (kbId: string) => {
    if (selectedKBs.includes(kbId)) {
      onSelectionChange(selectedKBs.filter((id) => id !== kbId));
    } else {
      onSelectionChange([...selectedKBs, kbId]);
    }
  };

  const handleSelectAll = () => {
    const activeKBs = availableKBs
      .filter((kb) => kb.status === "active" && kb.indexReady !== false)
      .map((kb) => kb.id);
    onSelectionChange(activeKBs);
  };

  const handleClearAll = () => {
    onSelectionChange([]);
  };

  return (
    <Card className="p-6 mb-6">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-semibold text-foreground">
          Select Knowledge Bases
        </h3>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={handleSelectAll}
            disabled={disabled === true}
            className="text-sm text-brand hover:text-brand-strong disabled:text-dim"
          >
            Select All
          </button>
          <span className="text-border">|</span>
          <button
            type="button"
            onClick={handleClearAll}
            disabled={disabled === true}
            className="text-sm text-brand hover:text-brand-strong disabled:text-dim"
          >
            Clear
          </button>
        </div>
      </div>

      <div className="space-y-2">
        {availableKBs.length === 0 ? (
          <p className="text-dim text-sm">No knowledge bases available</p>
        ) : (
          availableKBs.map((kb) => (
            <KBItem
              key={kb.id}
              kb={kb}
              isSelected={selectedKBs.includes(kb.id)}
              disabled={disabled}
              onToggle={handleToggle}
            />
          ))
        )}
      </div>

      {selectedKBs.length > 0 && (
        <div className="mt-3 text-sm text-secondary">
          {selectedKBs.length} knowledge base
          {selectedKBs.length !== 1 ? "s" : ""} selected
        </div>
      )}
    </Card>
  );
}



