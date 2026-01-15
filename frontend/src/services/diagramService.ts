import { DiagramSetResponse } from "../types/api";
import { keysToSnake } from "../utils/apiMapping";
import { API_BASE } from "./config";
import { fetchWithErrorHandling } from "./serviceError";

export const diagramApi = {
  async getDiagramSet(diagramSetId: string): Promise<DiagramSetResponse> {
    return fetchWithErrorHandling<DiagramSetResponse>(
      `${API_BASE}/v1/diagram-sets/${diagramSetId}`,
      {},
      "get diagram set"
    );
  },

  async createDiagramSet(
    inputDescription: string,
    adrId?: string
  ): Promise<DiagramSetResponse> {
    return fetchWithErrorHandling<DiagramSetResponse>(
      `${API_BASE}/v1/diagram-sets`,
      {
        method: "POST",
        headers: {
          // eslint-disable-next-line @typescript-eslint/naming-convention
          "Content-Type": "application/json",
        },
        body: JSON.stringify(
          keysToSnake({
            inputDescription,
            adrId,
          })
        ),
      },
      "create diagram set"
    );
  },
};
