/**
 * KB Routes - Proxy to Python service for generic KB operations
 * Handles /api/kb/* and /api/query/* endpoints for multi-KB queries
 */

import { Router, Request, Response } from "express";
import { logger } from "../logger.js";

export const router = Router();

const PYTHON_SERVICE_URL =
  process.env.PYTHON_SERVICE_URL || "http://localhost:8000";

/**
 * Proxy /kb/health to Python service
 */
router.get("/kb/health", async (_req: Request, res: Response) => {
  const url = `${PYTHON_SERVICE_URL}/kb/health`;
  logger.info(`[KB] Proxying GET /kb/health -> ${url}`);

  try {
    const response = await fetch(url);
    const data = await response.json();

    if (!response.ok) {
      logger.error(`[KB] Python service error: ${response.status}`, data);
      return res.status(response.status).json(data);
    }

    return res.json(data);
  } catch (error: any) {
    logger.error(`[KB] Proxy error: ${error.message}`);
    return res
      .status(500)
      .json({ error: "Failed to connect to Python service" });
  }
});

/**
 * Proxy /query/chat to Python service (multi-KB chat queries)
 */
router.post("/query/chat", async (req: Request, res: Response) => {
  const url = `${PYTHON_SERVICE_URL}/query/chat`;
  logger.info(`[Query] Proxying POST /query/chat -> ${url}`);
  logger.info(`[Query] Request body:`, req.body);

  try {
    const response = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(req.body),
    });

    const data = (await response.json()) as any;

    if (!response.ok) {
      logger.error(`[Query] Python service error: ${response.status}`, data);
      return res.status(response.status).json(data);
    }

    logger.info(
      `[Query] Success - returned ${data.sources?.length || 0} sources`
    );
    return res.json(data);
  } catch (error: any) {
    logger.error(`[Query] Proxy error: ${error.message}`);
    return res
      .status(500)
      .json({ error: "Failed to connect to Python service" });
  }
});
