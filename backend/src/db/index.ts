// Database module with SQLite
import sqlite3 from "sqlite3";
import { logger } from "../logger.js";
import path from "path";
import { fileURLToPath } from "url";
import fs from "fs";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Database path in the data directory
const DB_PATH = path.join(__dirname, "..", "..", "..", "data", "projects.db");

let db: sqlite3.Database | null = null;

export function initDatabase(): Promise<void> {
  return new Promise((resolve, reject) => {
    // Ensure data directory exists
    const dataDir = path.dirname(DB_PATH);
    if (!fs.existsSync(dataDir)) {
      fs.mkdirSync(dataDir, { recursive: true });
    }

    logger.info("Initializing SQLite database", { path: DB_PATH });

    db = new sqlite3.Database(DB_PATH, (err) => {
      if (err) {
        logger.error("Failed to open database", err);
        reject(err);
        return;
      }

      logger.info("Database connection established");

      // Create tables
      db!.serialize(() => {
        // Projects table
        db!.run(`
          CREATE TABLE IF NOT EXISTS projects (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            textRequirements TEXT,
            createdAt TEXT NOT NULL
          )
        `);

        // Documents table
        db!.run(`
          CREATE TABLE IF NOT EXISTS documents (
            id TEXT PRIMARY KEY,
            projectId TEXT NOT NULL,
            fileName TEXT NOT NULL,
            mimeType TEXT NOT NULL,
            rawText TEXT NOT NULL,
            uploadedAt TEXT NOT NULL,
            FOREIGN KEY(projectId) REFERENCES projects(id) ON DELETE CASCADE
          )
        `);

        // Project states table
        db!.run(`
          CREATE TABLE IF NOT EXISTS project_states (
            projectId TEXT PRIMARY KEY,
            state TEXT NOT NULL,
            updatedAt TEXT NOT NULL,
            FOREIGN KEY(projectId) REFERENCES projects(id) ON DELETE CASCADE
          )
        `);

        // Messages table
        db!.run(
          `
          CREATE TABLE IF NOT EXISTS messages (
            id TEXT PRIMARY KEY,
            projectId TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            wafSources TEXT,
            FOREIGN KEY(projectId) REFERENCES projects(id) ON DELETE CASCADE
          )
        `,
          (err) => {
            if (err) {
              logger.error("Failed to create tables", err);
              reject(err);
            } else {
              logger.info("Database tables initialized");
              resolve();
            }
          }
        );
      });
    });
  });
}

export function closeDatabase(): Promise<void> {
  return new Promise((resolve, reject) => {
    if (!db) {
      resolve();
      return;
    }

    db.close((err) => {
      if (err) {
        logger.error("Error closing database", err);
        reject(err);
      } else {
        logger.info("Database connection closed");
        db = null;
        resolve();
      }
    });
  });
}

export function getDatabase(): sqlite3.Database {
  if (!db) {
    throw new Error("Database not initialized");
  }
  return db;
}
