interface DiagramSetHeaderProps {
  readonly id: string;
  readonly adrId?: string;
  readonly createdAt: string;
  readonly diagramCount: number;
}

export function DiagramSetHeader({
  id,
  adrId,
  createdAt,
  diagramCount,
}: DiagramSetHeaderProps) {
  return (
    <div className="border-b border-gray-200 pb-6">
      <h1 className="text-3xl font-bold text-gray-900 mb-2">
        Architecture Diagrams
      </h1>
      <div className="flex items-center gap-4 text-sm text-gray-600">
        <span>Diagram Set ID: {id}</span>
        {adrId !== undefined && adrId !== "" && <span>ADR: {adrId}</span>}
        <span>Created: {new Date(createdAt).toLocaleDateString()}</span>
        <span className="font-medium text-blue-600">
          {diagramCount} diagrams
        </span>
      </div>
    </div>
  );
}
