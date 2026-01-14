import { isRecord } from "../../utils/typeGuards";

interface DiagramData {
  id: string;
  diagram_type: string;
  source_code: string;
  version: string;
  created_at: string;
}

interface Ambiguity {
  id: string;
  resolved: boolean;
  ambiguous_text?: string;
  suggested_clarification?: string;
}

interface DiagramSetResponse {
  id: string;
  adr_id?: string;
  input_description: string;
  diagrams: DiagramData[];
  ambiguities: Ambiguity[];
  created_at: string;
  updated_at: string;
}

export function normalizeDiagramSet(data: unknown): DiagramSetResponse | null {
  if (!isRecord(data)) return null;
  const ambiguities = Array.isArray(data.ambiguities)
    ? data.ambiguities.map((a) => {
        if (!isRecord(a)) return { id: "", resolved: false } as Ambiguity;
        return {
          id: String(a.id ?? ""),
          resolved: Boolean(a.resolved ?? false),
          ambiguous_text: typeof a.ambiguous_text === "string" ? a.ambiguous_text : typeof a.text_fragment === "string" ? a.text_fragment : undefined,
          suggested_clarification: typeof a.suggested_clarification === "string" ? a.suggested_clarification : undefined,
        } as Ambiguity;
      })
    : [];

  const diagrams = Array.isArray(data.diagrams)
    ? data.diagrams
        .filter(isRecord)
        .map((d) => ({
          id: String(d.id ?? ""),
          diagram_type: String(d.diagram_type ?? ""),
          source_code: String(d.source_code ?? ""),
          version: String(d.version ?? ""),
          created_at: String(d.created_at ?? ""),
        }))
    : [];

  return {
    id: String(data.id ?? ""),
    adr_id: typeof data.adr_id === "string" ? data.adr_id : undefined,
    input_description: String(data.input_description ?? ""),
    diagrams,
    ambiguities,
    created_at: String(data.created_at ?? ""),
    updated_at: String(data.updated_at ?? ""),
  };
}
