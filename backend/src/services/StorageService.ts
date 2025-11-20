import {
  Project,
  ProjectDocument,
  ProjectState,
  ConversationMessage,
} from "../models/Project.js";

class InMemoryStorage {
  private projects: Map<string, Project> = new Map();
  private documents: Map<string, ProjectDocument[]> = new Map();
  private states: Map<string, ProjectState> = new Map();
  private messages: Map<string, ConversationMessage[]> = new Map();

  // Projects
  createProject(project: Project): Project {
    this.projects.set(project.id, project);
    this.documents.set(project.id, []);
    this.messages.set(project.id, []);
    return project;
  }

  getProject(id: string): Project | undefined {
    return this.projects.get(id);
  }

  getAllProjects(): Project[] {
    return Array.from(this.projects.values());
  }

  // Documents
  addDocument(document: ProjectDocument): ProjectDocument {
    const docs = this.documents.get(document.projectId) || [];
    docs.push(document);
    this.documents.set(document.projectId, docs);
    return document;
  }

  getDocuments(projectId: string): ProjectDocument[] {
    return this.documents.get(projectId) || [];
  }

  // Project State
  saveState(state: ProjectState): ProjectState {
    this.states.set(state.projectId, state);
    return state;
  }

  getState(projectId: string): ProjectState | undefined {
    return this.states.get(projectId);
  }

  // Messages
  addMessage(message: ConversationMessage): ConversationMessage {
    const msgs = this.messages.get(message.projectId) || [];
    msgs.push(message);
    this.messages.set(message.projectId, msgs);
    return message;
  }

  getMessages(projectId: string, limit?: number): ConversationMessage[] {
    const msgs = this.messages.get(projectId) || [];
    if (limit) {
      return msgs.slice(-limit);
    }
    return msgs;
  }

  // Utility
  clear(): void {
    this.projects.clear();
    this.documents.clear();
    this.states.clear();
    this.messages.clear();
  }
}

export const storage = new InMemoryStorage();
