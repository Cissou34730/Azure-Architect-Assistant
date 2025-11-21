import { Router, Request, Response } from "express";
import multer from "multer";
import { randomUUID } from "crypto";
import { storage } from "../services/StorageService.js";
import { llmService } from "../services/LLMService.js";
import { logger } from "../logger.js";
import {
  Project,
  ProjectDocument,
  ConversationMessage,
} from "../models/Project.js";

export const router = Router();
const log = logger.child("ProjectsAPI");

// Configure multer for file uploads (memory storage)
const upload = multer({ storage: multer.memoryStorage() });

/**
 * 1. POST /projects
 * Create a new project
 */
router.post("/projects", (req: Request, res: Response) => {
  try {
    const { name } = req.body as {
      name?: string;
    };

    if (!name || typeof name !== "string" || name.trim() === "") {
      res.status(400).json({ error: "Project name is required" });
      return;
    }

    const project: Project = {
      id: randomUUID(),
      name: name.trim(),
      createdAt: new Date().toISOString(),
    };

    storage.createProject(project);
    log.info("Project created", { projectId: project.id, name: project.name });

    res.status(201).json({ project });
  } catch (error) {
    log.error("Error creating project", error);
    res.status(500).json({ error: "Failed to create project" });
  }
});

/**
 * GET /projects
 * List all projects
 */
router.get("/projects", (_req: Request, res: Response) => {
  try {
    const projects = storage.getAllProjects();
    log.info("Listing projects", { count: projects.length });
    res.json({ projects });
  } catch (error) {
    log.error("Error fetching projects", error);
    res.status(500).json({ error: "Failed to fetch projects" });
  }
});

/**
 * PUT /projects/:id/requirements
 * Update text requirements for a project
 */
router.put("/projects/:id/requirements", (req: Request, res: Response) => {
  try {
    const { id } = req.params;
    const { textRequirements } = req.body as { textRequirements?: string };

    const project = storage.getProject(id);
    if (!project) {
      res.status(404).json({ error: "Project not found" });
      return;
    }

    project.textRequirements =
      textRequirements && typeof textRequirements === "string"
        ? textRequirements.trim()
        : undefined;
    storage.createProject(project); // Update project in storage

    log.info("Updated project requirements", {
      projectId: project.id,
      hasText: Boolean(project.textRequirements),
    });

    res.json({ project });
  } catch (error) {
    log.error("Error updating requirements", error);
    res.status(500).json({ error: "Failed to update requirements" });
  }
});

/**
 * 2. POST /projects/:id/documents
 * Upload documents to a project
 */
router.post(
  "/projects/:id/documents",
  upload.array("files"),
  (req: Request, res: Response) => {
    try {
      const { id } = req.params;
      const files = req.files as Express.Multer.File[];

      const project = storage.getProject(id);
      if (!project) {
        res.status(404).json({ error: "Project not found" });
        return;
      }

      if (!files || files.length === 0) {
        res.status(400).json({ error: "No files uploaded" });
        return;
      }

      const documents: ProjectDocument[] = [];

      for (const file of files) {
        // Extract text based on MIME type
        let rawText: string;

        if (file.mimetype.startsWith("text/")) {
          // Plain text files
          rawText = file.buffer.toString("utf-8");
        } else if (file.mimetype === "application/pdf") {
          // Placeholder for PDF extraction
          rawText = `[PDF Document: ${file.originalname}]\n[Text extraction not implemented in POC - placeholder content]`;
        } else if (
          file.mimetype ===
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document" ||
          file.mimetype === "application/msword"
        ) {
          // Placeholder for DOCX/DOC extraction
          rawText = `[Word Document: ${file.originalname}]\n[Text extraction not implemented in POC - placeholder content]`;
        } else {
          rawText = `[File: ${file.originalname}]\n[Unsupported file type for text extraction]`;
        }

        const document: ProjectDocument = {
          id: randomUUID(),
          projectId: id,
          fileName: file.originalname,
          mimeType: file.mimetype,
          rawText,
          uploadedAt: new Date().toISOString(),
        };

        storage.addDocument(document);
        documents.push(document);
      }

      log.info("Documents uploaded", {
        projectId: id,
        documents: documents.length,
      });

      res.status(201).json({ documents });
    } catch (error) {
      log.error("Error uploading documents", error);
      res.status(500).json({ error: "Failed to upload documents" });
    }
  }
);

/**
 * 3. POST /projects/:id/analyze-docs
 * Analyze all documents and generate initial ProjectState
 */
router.post(
  "/projects/:id/analyze-docs",
  async (req: Request, res: Response) => {
    try {
      const { id } = req.params;

      const project = storage.getProject(id);
      if (!project) {
        res.status(404).json({ error: "Project not found" });
        return;
      }

      const documents = storage.getDocuments(id);

      // Collect text sources: documents + text requirements
      const documentTexts = documents.map((doc) => doc.rawText);
      if (project.textRequirements) {
        documentTexts.push(project.textRequirements);
      }

      if (documentTexts.length === 0) {
        res
          .status(400)
          .json({ error: "No documents or text requirements to analyze" });
        return;
      }

      log.info("Document analysis requested", {
        projectId: id,
        documentCount: documentTexts.length,
      });

      // Call LLM to analyze documents
      const projectState = await llmService.analyzeDocuments(documentTexts);
      projectState.projectId = id;

      // Save state
      storage.saveState(projectState);

      log.info("Document analysis completed", { projectId: id });
      res.json({ projectState });
    } catch (error) {
      log.error("Error analyzing documents", error);
      res.status(500).json({
        error: "Failed to analyze documents",
        details: error instanceof Error ? error.message : String(error),
      });
    }
  }
);

/**
 * 4. POST /projects/:id/chat
 * Send a chat message and get response with updated state
 */
router.post("/projects/:id/chat", async (req: Request, res: Response) => {
  try {
    const { id } = req.params;
    const { message } = req.body as { message?: string };

    if (!message || typeof message !== "string") {
      res.status(400).json({ error: "Message is required" });
      return;
    }

    const project = storage.getProject(id);
    if (!project) {
      res.status(404).json({ error: "Project not found" });
      return;
    }

    const currentState = storage.getState(id);
    if (!currentState) {
      res.status(400).json({
        error: "Project state not initialized. Please analyze documents first.",
      });
      return;
    }

    // Save user message
    const userMessage: ConversationMessage = {
      id: randomUUID(),
      projectId: id,
      role: "user",
      content: message,
      timestamp: new Date().toISOString(),
    };
    storage.addMessage(userMessage);

    // Get recent conversation history (last 10 messages)
    const recentMessages = storage.getMessages(id, 10);

    log.info("Processing chat message", {
      projectId: id,
      messageLength: message.length,
      historyCount: recentMessages.length,
    });

    // Process with LLM
    const response = await llmService.processChatMessage(
      message,
      currentState,
      recentMessages
    );

    // Save assistant message
    const assistantMessage: ConversationMessage = {
      id: randomUUID(),
      projectId: id,
      role: "assistant",
      content:
        response.assistantMessage || "I've updated the architecture sheet.",
      timestamp: new Date().toISOString(),
    };
    storage.addMessage(assistantMessage);

    // Update project state
    storage.saveState(response.projectState);

    log.info("Chat response generated", { projectId: id });
    res.json({
      message: assistantMessage.content,
      projectState: response.projectState,
    });
  } catch (error) {
    log.error("Error processing chat", error);
    res.status(500).json({
      error: "Failed to process chat message",
      details: error instanceof Error ? error.message : String(error),
    });
  }
});

/**
 * 5. GET /projects/:id/state
 * Get current project state (Architecture Sheet)
 */
router.get("/projects/:id/state", (req: Request, res: Response) => {
  try {
    const { id } = req.params;

    const project = storage.getProject(id);
    if (!project) {
      res.status(404).json({ error: "Project not found" });
      return;
    }

    const state = storage.getState(id);
    if (!state) {
      res.status(404).json({ error: "Project state not initialized" });
      return;
    }

    log.info("Returning project state", { projectId: id });
    res.json({ projectState: state });
  } catch (error) {
    log.error("Error fetching state", error);
    res.status(500).json({ error: "Failed to fetch project state" });
  }
});

/**
 * 6. POST /projects/:id/architecture/proposal
 * Generate Azure architecture proposal
 */
router.post(
  "/projects/:id/architecture/proposal",
  async (req: Request, res: Response) => {
    try {
      const { id } = req.params;

      const project = storage.getProject(id);
      if (!project) {
        res.status(404).json({ error: "Project not found" });
        return;
      }

      const state = storage.getState(id);
      if (!state) {
        res.status(400).json({
          error:
            "Project state not initialized. Please analyze documents first.",
        });
        return;
      }

      log.info("Generating architecture proposal", { projectId: id });

      // Generate architecture proposal
      const proposal = await llmService.generateArchitectureProposal(state);

      res.json({ proposal });
    } catch (error) {
      log.error("Error generating proposal", error);
      res.status(500).json({
        error: "Failed to generate architecture proposal",
        details: error instanceof Error ? error.message : String(error),
      });
    }
  }
);

/**
 * GET /projects/:id/messages
 * Get conversation history
 */
router.get("/projects/:id/messages", (req: Request, res: Response) => {
  try {
    const { id } = req.params;

    const project = storage.getProject(id);
    if (!project) {
      res.status(404).json({ error: "Project not found" });
      return;
    }

    const messages = storage.getMessages(id);
    log.info("Returning messages", { projectId: id, count: messages.length });
    res.json({ messages });
  } catch (error) {
    log.error("Error fetching messages", error);
    res.status(500).json({ error: "Failed to fetch messages" });
  }
});
