import sqlite3 from "sqlite3";
import path from "path";
import { fileURLToPath } from "url";
import { dirname } from "path";
import { logger } from "./logger.js";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const DB_PATH = path.join(__dirname, "..", "data", "database.sqlite");

export const db = new sqlite3.Database(DB_PATH, (err) => {
  if (err) {
    logger.error("Error opening database", err.message);
  } else {
    logger.info("Connected to SQLite database");
  }
});

export function initDatabase(): void {
  db.serialize(() => {
    db.run(`
      CREATE TABLE IF NOT EXISTS items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
      )
    `);

    logger.info("Database initialized");
  });
}

export function closeDatabase(): Promise<void> {
  return new Promise((resolve, reject) => {
    db.close((err) => {
      if (err) {
        reject(err);
      } else {
        logger.info("Database connection closed");
        resolve();
      }
    });
  });
}
