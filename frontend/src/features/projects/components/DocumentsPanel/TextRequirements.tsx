interface TextRequirementsProps {
  readonly text: string;
  readonly onChange: (text: string) => void;
  readonly onSave: () => void;
  readonly loading: boolean;
}

export function TextRequirements({
  text,
  onChange,
  onSave,
  loading,
}: TextRequirementsProps) {
  return (
    <div className="mb-6">
      <h3 className="font-semibold mb-2">Text Requirements</h3>
      <textarea
        value={text}
        onChange={(e) => {
          onChange(e.target.value);
        }}
        placeholder="Describe your project requirements here..."
        className="w-full px-3 py-2 border border-gray-300 rounded-md mb-2 text-sm"
        rows={5}
      />
      <button
        onClick={onSave}
        disabled={loading}
        className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 disabled:opacity-50 mb-4"
      >
        Save Requirements
      </button>
    </div>
  );
}
