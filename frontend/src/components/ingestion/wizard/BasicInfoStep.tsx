/**
 * Basic Information Step Component
 */

interface BasicInfoStepProps {
  name: string;
  setName: (value: string) => void;
  kbId: string;
  setKbId: (value: string) => void;
  description: string;
  setDescription: (value: string) => void;
}

export function BasicInfoStep({
  name,
  setName,
  kbId,
  setKbId,
  description,
  setDescription,
}: BasicInfoStepProps) {
  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold text-gray-900">Basic Information</h3>

      <div>
        <label
          htmlFor="kb-name"
          className="block text-sm font-medium text-gray-700 mb-1"
        >
          Name *
        </label>
        <input
          id="kb-name"
          type="text"
          value={name}
          onChange={(e) => { setName(e.target.value); }}
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          placeholder="e.g., Azure Architecture"
        />
      </div>

      <div>
        <label
          htmlFor="kb-id"
          className="block text-sm font-medium text-gray-700 mb-1"
        >
          KB ID *
        </label>
        <input
          id="kb-id"
          type="text"
          value={kbId}
          onChange={(e) => { setKbId(e.target.value); }}
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          placeholder="e.g., azure-arch"
        />
        <p className="mt-1 text-xs text-gray-500">
          Unique identifier (lowercase, hyphens only)
        </p>
      </div>

      <div>
        <label
          htmlFor="kb-description"
          className="block text-sm font-medium text-gray-700 mb-1"
        >
          Description
        </label>
        <textarea
          id="kb-description"
          value={description}
          onChange={(e) => { setDescription(e.target.value); }}
          rows={3}
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          placeholder="Brief description of this knowledge base"
        />
      </div>
    </div>
  );
}
