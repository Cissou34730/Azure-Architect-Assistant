import { isRecord } from "../../utils/typeGuards";
import { DiagramSetResponse, DiagramData, Ambiguity } from "../../types/api";

// eslint-disable-next-line @typescript-eslint/no-restricted-types
function normalizeAmbiguity(a: unknown): Ambiguity {
  if (!isRecord(a)) {
    return {
      id: "",
      diagramSetId: "",
      ambiguousText: "",
      resolved: false,
      createdAt: "",
    };
  }

  return {
    id:
      typeof a.id === "string"
        ? a.id
        : typeof a.id === "number"
        ? String(a.id)
        : "",
    diagramSetId: typeof a.diagram_set_id === "string" ? a.diagram_set_id : "",
    ambiguousText:
      typeof a.ambiguous_text === "string"
        ? a.ambiguous_text
        : typeof a.text_fragment === "string"
        ? a.text_fragment
        : "",
    suggestedClarification:
      typeof a.suggested_clarification === "string"
        ? a.suggested_clarification
        : undefined,
    resolved: Boolean(a.resolved ?? false),
    createdAt: typeof a.created_at === "string" ? a.created_at : "",
  };
}

// eslint-disable-next-line @typescript-eslint/no-restricted-types
function normalizeDiagram(d: unknown): DiagramData {
  if (!isRecord(d)) {
    return {
      id: "",
      diagramType: "",
      sourceCode: "",
      version: "",
      createdAt: "",
    };
  }

  return {
    id:
      typeof d.id === "string"
        ? d.id
        : typeof d.id === "number"
        ? String(d.id)
        : "",
    diagramType: typeof d.diagram_type === "string" ? d.diagram_type : "",
    sourceCode: typeof d.source_code === "string" ? d.source_code : "",
    version: typeof d.version === "string" ? d.version : "",
    createdAt: typeof d.created_at === "string" ? d.created_at : "",
  };
}

// eslint-disable-next-line @typescript-eslint/no-restricted-types
export function normalizeDiagramSet(data: unknown): DiagramSetResponse | null {
  if (!isRecord(data)) {
    return null;
  }

  const ambiguities = Array.isArray(data.ambiguities)
    ? data.ambiguities.map(normalizeAmbiguity)
    : [];

  const diagrams = Array.isArray(data.diagrams)
    ? data.diagrams.map(normalizeDiagram)
    : [];

  return {
    id:
      typeof data.id === "string"
        ? data.id
        : typeof data.id === "number"
        ? String(data.id)
        : "",
    adrId: typeof data.adr_id === "string" ? data.adr_id : undefined,
    inputDescription:
      typeof data.input_description === "string" ? data.input_description : "",
    diagrams,
    ambiguities,
    createdAt: typeof data.created_at === "string" ? data.created_at : "",
    updatedAt: typeof data.updated_at === "string" ? data.updated_at : "",
  };
}
