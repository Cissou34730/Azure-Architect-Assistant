import { Router, Request, Response } from "express";
import { db } from "../db.js";

export const router = Router();

interface Item {
  id: number;
  name: string;
  description: string;
  created_at: string;
}

// GET all items
router.get("/items", (_req: Request, res: Response) => {
  db.all(
    "SELECT * FROM items ORDER BY created_at DESC",
    [],
    (err, rows: Item[]) => {
      if (err) {
        res.status(500).json({ error: err.message });
        return;
      }
      res.json({ items: rows });
    }
  );
});

// POST new item
router.post("/items", (req: Request, res: Response) => {
  const { name, description } = req.body as {
    name: string;
    description: string;
  };

  if (!name) {
    res.status(400).json({ error: "Name is required" });
    return;
  }

  db.run(
    "INSERT INTO items (name, description) VALUES (?, ?)",
    [name, description],
    function (err) {
      if (err) {
        res.status(500).json({ error: err.message });
        return;
      }
      res.status(201).json({ id: this.lastID, name, description });
    }
  );
});

// DELETE item
router.delete("/items/:id", (req: Request, res: Response) => {
  const { id } = req.params;

  db.run("DELETE FROM items WHERE id = ?", [id], function (err) {
    if (err) {
      res.status(500).json({ error: err.message });
      return;
    }
    if (this.changes === 0) {
      res.status(404).json({ error: "Item not found" });
      return;
    }
    res.json({ message: "Item deleted", id });
  });
});
