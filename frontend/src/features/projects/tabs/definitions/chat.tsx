import { ProjectTab } from "../types";
import { ChatTabAdapter } from "../adapters/ChatTabAdapter";

export const chatTab: ProjectTab = {
  id: "chat",
  label: "Chat",
  path: "chat",
  component: ChatTabAdapter,
};
