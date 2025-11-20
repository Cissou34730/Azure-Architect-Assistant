import type { Item } from "../models/Item.js";

// Note: This service is not used in the POC
// The POC uses StorageService for in-memory storage instead

export class ItemService {
  async getAllItems(): Promise<Item[]> {
    // Not implemented - using in-memory storage
    return Promise.resolve([]);
  }

  async createItem(
    name: string,
    description?: string
  ): Promise<{ id: number; name: string; description?: string }> {
    // Not implemented - using in-memory storage
    return Promise.resolve({ id: 0, name, description });
  }

  async deleteItem(id: string): Promise<{ message: string; id: string }> {
    // Not implemented - using in-memory storage
    return Promise.resolve({ message: "Item deleted", id });
  }
}
