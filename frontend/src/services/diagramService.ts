const API_BASE = `${import.meta.env.BACKEND_URL}/api`;

export const diagramApi = {
  async getDiagramSet(diagramSetId: string) {
    const response = await fetch(`${API_BASE}/diagrams/${diagramSetId}`);
    if (!response.ok) {
      throw new Error(`Failed to fetch diagram set: ${response.statusText}`);
    }
    return response.json();
  },

  async createDiagramSet(inputDescription: string, adrId?: string) {
    const response = await fetch(`${API_BASE}/diagrams/generate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        input_description: inputDescription,
        adr_id: adrId,
      }),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(
        errorData.detail ||
          `Failed to create diagram set: ${response.statusText}`
      );
    }
    return response.json();
  },
};
