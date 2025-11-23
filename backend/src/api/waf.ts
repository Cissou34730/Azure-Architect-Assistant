/**
 * WAF Routes
 * Endpoints for Azure Well-Architected Framework query functionality
 */

import { Router, Request, Response } from "express";
import { wafService, WAFQueryRequest } from "../services/WAFService.js";
import { logger } from "../logger.js";

export const router = Router();

/**
 * POST /api/waf/query
 * Query the WAF documentation
 */
router.post("/waf/query", async (req: Request, res: Response) => {
  try {
    const { question, topK, metadataFilters } = req.body as WAFQueryRequest;

    if (!question || typeof question !== "string") {
      return res.status(400).json({
        error: "Question is required and must be a string",
      });
    }

    logger.info("WAF query request received", { question });

    const result = await wafService.query({
      question,
      topK,
      metadataFilters,
    });

    return res.json(result);
  } catch (error) {
    logger.error("WAF query endpoint error", { error });
    return res.status(500).json({
      error: "Failed to process WAF query",
      message: error instanceof Error ? error.message : "Unknown error",
    });
  }
});

/**
 * POST /api/waf/ingest
 * Start WAF ingestion pipeline
 */
router.post("/waf/ingest", (_req: Request, res: Response) => {
  try {
    logger.info("WAF ingestion request received");

    const result = wafService.startIngestion();

    return res.json(result);
  } catch (error) {
    logger.error("WAF ingestion endpoint error", { error });
    return res.status(500).json({
      error: "Failed to start WAF ingestion",
      message: error instanceof Error ? error.message : "Unknown error",
    });
  }
});

/**
 * GET /api/waf/status
 * Get WAF ingestion status
 */
router.get("/waf/status", async (_req: Request, res: Response) => {
  try {
    const status = await wafService.getIngestionStatus();
    res.json(status);
  } catch (error) {
    logger.error("WAF status endpoint error", { error });
    res.status(500).json({
      error: "Failed to get WAF status",
      message: error instanceof Error ? error.message : "Unknown error",
    });
  }
});

/**
 * GET /api/waf/ready
 * Check if WAF index is ready for queries
 */
router.get("/waf/ready", async (_req: Request, res: Response) => {
  try {
    const isReady = await wafService.isIndexReady();
    res.json({ ready: isReady });
  } catch (error) {
    logger.error("WAF ready check error", { error });
    res.status(500).json({
      error: "Failed to check WAF readiness",
      message: error instanceof Error ? error.message : "Unknown error",
    });
  }
});
