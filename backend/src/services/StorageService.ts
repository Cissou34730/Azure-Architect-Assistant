import {
  Project,
  ProjectDocument,
  ProjectState,
  ConversationMessage,
} from "../models/Project.js";
import { getDatabase } from "../db/index.js";
import { logger } from "../logger.js";

const log = logger.child("StorageService");

class SQLiteStorage {
  // Projects
  createProject(project: Project): Promise<Project> {
    return new Promise((resolve, reject) => {
      const db = getDatabase();
      db.run(
        `INSERT INTO projects (id, name, textRequirements, createdAt) VALUES (?, ?, ?, ?)`,
        [
          project.id,
          project.name,
          project.textRequirements || null,
          project.createdAt,
        ],
        (err) => {
          if (err) {
            log.error("Failed to create project", err);
            reject(err);
          } else {
            log.info("Project created", { projectId: project.id });
            resolve(project);
          }
        }
      );
    });
  }

  getProject(id: string): Promise<Project | undefined> {
    return new Promise((resolve, reject) => {
      const db = getDatabase();
      db.get(`SELECT * FROM projects WHERE id = ?`, [id], (err, row: any) => {
        if (err) {
          log.error("Failed to get project", err);
          reject(err);
        } else {
          resolve(row as Project);
        }
      });
    });
  }

  getAllProjects(): Promise<Project[]> {
    return new Promise((resolve, reject) => {
      const db = getDatabase();
      db.all(
        `SELECT * FROM projects ORDER BY createdAt DESC`,
        (err, rows: any[]) => {
          if (err) {
            log.error("Failed to get all projects", err);
            reject(err);
          } else {
            resolve(rows as Project[]);
          }
        }
      );
    });
  }

  updateProjectRequirements(
    id: string,
    textRequirements: string
  ): Promise<void> {
    return new Promise((resolve, reject) => {
      const db = getDatabase();
      db.run(
        `UPDATE projects SET textRequirements = ? WHERE id = ?`,
        [textRequirements, id],
        (err) => {
          if (err) {
            log.error("Failed to update project requirements", err);
            reject(err);
          } else {
            log.info("Project requirements updated", { projectId: id });
            resolve();
          }
        }
      );
    });
  }

  // Documents
  addDocument(document: ProjectDocument): Promise<ProjectDocument> {
    return new Promise((resolve, reject) => {
      const db = getDatabase();
      db.run(
        `INSERT INTO documents (id, projectId, fileName, mimeType, rawText, uploadedAt) VALUES (?, ?, ?, ?, ?, ?)`,
        [
          document.id,
          document.projectId,
          document.fileName,
          document.mimeType,
          document.rawText,
          document.uploadedAt,
        ],
        (err) => {
          if (err) {
            log.error("Failed to add document", err);
            reject(err);
          } else {
            log.info("Document added", {
              documentId: document.id,
              projectId: document.projectId,
            });
            resolve(document);
          }
        }
      );
    });
  }

  getDocuments(projectId: string): Promise<ProjectDocument[]> {
    return new Promise((resolve, reject) => {
      const db = getDatabase();
      db.all(
        `SELECT * FROM documents WHERE projectId = ? ORDER BY uploadedAt DESC`,
        [projectId],
        (err, rows: any[]) => {
          if (err) {
            log.error("Failed to get documents", err);
            reject(err);
          } else {
            resolve(rows as ProjectDocument[]);
          }
        }
      );
    });
  }

  // Project State
  saveState(state: ProjectState): Promise<ProjectState> {
    return new Promise((resolve, reject) => {
      const db = getDatabase();
      const stateJson = JSON.stringify(state);
      const now = new Date().toISOString();

      db.run(
        `INSERT OR REPLACE INTO project_states (projectId, state, updatedAt) VALUES (?, ?, ?)`,
        [state.projectId, stateJson, now],
        (err) => {
          if (err) {
            log.error("Failed to save state", err);
            reject(err);
          } else {
            log.info("Project state saved", { projectId: state.projectId });
            resolve(state);
          }
        }
      );
    });
  }

  getState(projectId: string): Promise<ProjectState | undefined> {
    return new Promise((resolve, reject) => {
      const db = getDatabase();
      db.get(
        `SELECT state FROM project_states WHERE projectId = ?`,
        [projectId],
        (err, row: any) => {
          if (err) {
            log.error("Failed to get state", err);
            reject(err);
          } else if (row) {
            try {
              const state = JSON.parse(row.state) as ProjectState;
              resolve(state);
            } catch (parseErr) {
              log.error("Failed to parse state JSON", parseErr);
              reject(parseErr);
            }
          } else {
            resolve(undefined);
          }
        }
      );
    });
  }

  // Messages
  addMessage(message: ConversationMessage): Promise<ConversationMessage> {
    return new Promise((resolve, reject) => {
      const db = getDatabase();
      const wafSourcesJson = message.wafSources
        ? JSON.stringify(message.wafSources)
        : null;

      db.run(
        `INSERT INTO messages (id, projectId, role, content, timestamp, wafSources) VALUES (?, ?, ?, ?, ?, ?)`,
        [
          message.id,
          message.projectId,
          message.role,
          message.content,
          message.timestamp,
          wafSourcesJson,
        ],
        (err) => {
          if (err) {
            log.error("Failed to add message", err);
            reject(err);
          } else {
            log.info("Message added", {
              messageId: message.id,
              projectId: message.projectId,
            });
            resolve(message);
          }
        }
      );
    });
  }

  getMessages(
    projectId: string,
    limit?: number
  ): Promise<ConversationMessage[]> {
    return new Promise((resolve, reject) => {
      const db = getDatabase();
      const query = limit
        ? `SELECT * FROM messages WHERE projectId = ? ORDER BY timestamp ASC LIMIT ?`
        : `SELECT * FROM messages WHERE projectId = ? ORDER BY timestamp ASC`;
      const params = limit ? [projectId, limit] : [projectId];

      db.all(query, params, (err, rows: any[]) => {
        if (err) {
          log.error("Failed to get messages", err);
          reject(err);
        } else {
          const messages = rows.map((row) => ({
            ...row,
            wafSources: row.wafSources ? JSON.parse(row.wafSources) : undefined,
          })) as ConversationMessage[];
          resolve(messages);
        }
      });
    });
  }

  // Utility
  clear(): Promise<void> {
    return new Promise((resolve, reject) => {
      const db = getDatabase();
      db.serialize(() => {
        db.run(`DELETE FROM messages`);
        db.run(`DELETE FROM project_states`);
        db.run(`DELETE FROM documents`);
        db.run(`DELETE FROM projects`, (err) => {
          if (err) {
            log.error("Failed to clear database", err);
            reject(err);
          } else {
            log.info("Database cleared");
            resolve();
          }
        });
      });
    });
  }
}

export const storage = new SQLiteStorage();
