export interface DiagramData {
  readonly id: string;
  readonly diagramType: string;
  readonly sourceCode: string;
  readonly version: string;
  readonly createdAt: string;
}

export interface Ambiguity {
  readonly id: string;
  readonly diagramSetId: string;
  readonly ambiguousText: string;
  readonly suggestedClarification?: string;
  readonly resolved: boolean;
  readonly createdAt: string;
  readonly textFragment?: string;
}

export interface DiagramSetResponse {
  readonly id: string;
  readonly adrId?: string;
  readonly inputDescription: string;
  readonly diagrams: readonly DiagramData[];
  readonly ambiguities: readonly Ambiguity[];
  readonly createdAt: string;
  readonly updatedAt: string;
}
