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
 * Start full WAF ingestion pipeline (Phase 1 + auto-approve + Phase 2)
 * Legacy endpoint - maintained for backward compatibility
 */
router.post("/waf/ingest", (_req: Request, res: Response) => {
  try {
    logger.info("WAF full ingestion request received");

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
 * POST /api/waf/ingest/phase1
 * Start WAF ingestion Phase 1 (crawl + clean + export)
 */
router.post("/waf/ingest/phase1", (_req: Request, res: Response) => {
  try {
    logger.info("WAF Phase 1 ingestion request received");

    const result = wafService.startIngestionPhase1();

    return res.json(result);
  } catch (error) {
    logger.error("WAF Phase 1 endpoint error", { error });
    return res.status(500).json({
      error: "Failed to start WAF Phase 1",
      message: error instanceof Error ? error.message : "Unknown error",
    });
  }
});

/**
 * POST /api/waf/ingest/phase2
 * Start WAF ingestion Phase 2 (chunk + embed + index)
 * Requires Phase 1 to be complete and documents to be validated
 */
router.post("/waf/ingest/phase2", (_req: Request, res: Response) => {
  try {
    logger.info("WAF Phase 2 ingestion request received");

    const result = wafService.startIngestionPhase2();

    return res.json(result);
  } catch (error) {
    logger.error("WAF Phase 2 endpoint error", { error });
    return res.status(500).json({
      error: "Failed to start WAF Phase 2",
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
