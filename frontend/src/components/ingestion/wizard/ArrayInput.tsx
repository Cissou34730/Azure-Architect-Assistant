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
      <label className="block text-sm font-medium text-gray-700 mb-2">
        {label}
      </label>
      <div className="space-y-2">
        {values.map((value, index) => (
          <div key={index} className="flex gap-2">
            <input
              type="text"
              value={value}
              onChange={(e) => updateField(index, e.target.value)}
              className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder={placeholder}
            />
            {values.length > 1 && (
              <button
                type="button"
                onClick={() => removeField(index)}
                className="px-3 py-2 text-red-600 hover:bg-red-50 rounded-md"
                aria-label={`Remove ${label} ${index + 1}`}
              >
                ×
              </button>
            )}
          </div>
        ))}
      </div>
      <button
        type="button"
        onClick={addField}
        className="mt-2 text-sm text-blue-600 hover:text-blue-700"
      >
        + Add another
      </button>
      {helpText && <p className="mt-1 text-xs text-gray-500">{helpText}</p>}
    </div>
  );
}
