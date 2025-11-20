import { Router, Request, Response } from "express";
import { ItemService } from "../services/ItemService.js";

export const router = Router();
const itemService = new ItemService();

// GET all items
router.get("/items", async (_req: Request, res: Response): Promise<void> => {
  try {
    const items = await itemService.getAllItems();
    res.json({ items });
  } catch (err) {
    const error = err as Error;
    res.status(500).json({ error: error.message });
  }
});

// POST new item
router.post("/items", async (req: Request, res: Response): Promise<void> => {
  try {
    const { name, description } = req.body as {
      name: string;
      description?: string;
    };

    if (!name) {
      res.status(400).json({ error: "Name is required" });
      return;
    }

    const item = await itemService.createItem(name, description);
    res.status(201).json(item);
  } catch (err) {
    const error = err as Error;
    res.status(500).json({ error: error.message });
  }
});

// DELETE item
router.delete(
  "/items/:id",
  async (req: Request, res: Response): Promise<void> => {
    try {
      const { id } = req.params;
      const result = await itemService.deleteItem(id);
      res.json(result);
    } catch (err) {
      const error = err as Error;
      if (error.message === "Item not found") {
        res.status(404).json({ error: error.message });
      } else {
        res.status(500).json({ error: error.message });
      }
    }
  }
);
