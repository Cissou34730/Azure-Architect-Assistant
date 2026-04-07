/**
 * Array input component for URL lists
 */

interface ArrayInputProps {
  label: string;
  values: string[];
  onChange: (values: string[]) => void;
  placeholder?: string;
  helpText?: string;
}

export function ArrayInput({
  label,
  values,
  onChange,
  placeholder,
  helpText,
}: ArrayInputProps) {
  const addField = () => {
    onChange([...values, ""]);
  };

  const removeField = (index: number) => {
    onChange(values.filter((_, i) => i !== index));
  };

  const updateField = (index: number, value: string) => {
    const newValues = [...values];
    newValues[index] = value;
    onChange(newValues);
  };

  return (
    <div>
      <label className="block text-sm font-medium text-secondary mb-2">
        {label}
      </label>
      <div className="space-y-2">
        {values.map((value, index) => {
          const key = `field-${index}`;
          return (
            <div key={key} className="flex gap-2">
              <input
                type="text"
                value={value}
                onChange={(e) => {
                  updateField(index, e.target.value);
                }}
                className="flex-1 px-3 py-2 border border-border-stronger rounded-md focus:outline-none focus:ring-2 focus:ring-brand"
                placeholder={placeholder}
              />
              {values.length > 1 && (
                <button
                  type="button"
                  onClick={() => {
                    removeField(index);
                  }}
                  className="px-3 py-2 text-danger hover:bg-danger-soft rounded-md"
                  aria-label={`Remove ${label} ${index + 1}`}
                >
                  ×
                </button>
              )}
            </div>
          );
        })}
      </div>
      <button
        type="button"
        onClick={addField}
        className="mt-2 text-sm text-brand hover:text-brand-strong"
      >
        + Add another
      </button>
      {helpText !== undefined && helpText !== "" && (
        <p className="mt-1 text-xs text-dim">{helpText}</p>
      )}
    </div>
  );
}


