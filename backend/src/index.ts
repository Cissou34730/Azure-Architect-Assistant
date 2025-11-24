import express, { Request, Response } from "express";
import cors from "cors";
import dotenv from "dotenv";
import { fileURLToPath } from "url";
import { dirname, join } from "path";
import { initDatabase } from "./db/index.js";
import { apiRouter } from "./api/index.js";
import { logger, configureLoggerFromEnv, getLogLevel } from "./logger.js";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// Load .env from project root (shared with Python service)
dotenv.config({ path: join(__dirname, "..", "..", ".env") });
configureLoggerFromEnv();
logger.info("Environment loaded", {
  openAiKey: process.env.OPENAI_API_KEY ? "SET" : "NOT SET",
  port: process.env.EXPRESS_PORT || 3000,
  pythonServiceUrl: process.env.PYTHON_SERVICE_URL || "http://localhost:8000",
  logLevel: getLogLevel(),
});

const app = express();
const PORT = process.env.EXPRESS_PORT ?? 3000;

// Middleware
app.use(cors());
app.use(express.json());

// Initialize database and start server
initDatabase()
  .then(() => {
    logger.info("Database initialized successfully");

    // Routes
    app.get("/health", (_req: Request, res: Response) => {
      logger.info("Health check requested");
      res.json({ status: "ok", timestamp: new Date().toISOString() });
    });

    app.use("/api", apiRouter);

    // Start server
    app.listen(PORT, () => {
      logger.info(`Server running on http://localhost:${PORT}`);
    });
  })
  .catch((error) => {
    logger.error("Failed to initialize database", error);
    process.exit(1);
  });
