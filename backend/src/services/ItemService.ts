import { db } from "../db/index.js";
import type { Item } from "../models/Item.js";

export class ItemService {
  async getAllItems(): Promise<Item[]> {
    return new Promise((resolve, reject) => {
      db.all(
        "SELECT * FROM items ORDER BY created_at DESC",
        [],
        (err, rows: Item[]) => {
          if (err) {
            reject(err);
          } else {
            resolve(rows);
          }
        }
      );
    });
  }

  async createItem(
    name: string,
    description?: string
  ): Promise<{ id: number; name: string; description?: string }> {
    return new Promise((resolve, reject) => {
      db.run(
        "INSERT INTO items (name, description) VALUES (?, ?)",
        [name, description],
        function (err) {
          if (err) {
            reject(err);
          } else {
            resolve({ id: this.lastID, name, description });
          }
        }
      );
    });
  }

  async deleteItem(id: string): Promise<{ message: string; id: string }> {
    return new Promise((resolve, reject) => {
      db.run("DELETE FROM items WHERE id = ?", [id], function (err) {
        if (err) {
          reject(err);
        } else if (this.changes === 0) {
          reject(new Error("Item not found"));
        } else {
          resolve({ message: "Item deleted", id });
        }
      });
    });
  }
}
