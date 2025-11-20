import express, { Request, Response } from "express";
import cors from "cors";
import dotenv from "dotenv";
import { initDatabase } from "./db/index.js";
import { apiRouter } from "./api/index.js";

dotenv.config();

const app = express();
const PORT = process.env.PORT ?? 3000;

// Middleware
app.use(cors());
app.use(express.json());

// Initialize database
initDatabase();

// Routes
app.get("/health", (_req: Request, res: Response) => {
  res.json({ status: "ok", timestamp: new Date().toISOString() });
});

app.use("/api", apiRouter);

// Start server
app.listen(PORT, () => {
  console.log(`🚀 Server running on http://localhost:${PORT}`);
});
