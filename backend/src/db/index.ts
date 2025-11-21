// Database module - not used in POC (in-memory storage only)
import { logger } from "../logger.js";

export function initDatabase(): void {
  logger.info("Using in-memory storage (no database)");
}

export function closeDatabase(): Promise<void> {
  return Promise.resolve();
}
