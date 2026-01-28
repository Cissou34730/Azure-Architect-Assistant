import type { ReactNode } from "react";

export type CommandCategory = "Navigation" | "Actions" | "Help";

export interface Command {
  readonly id: string;
  readonly label: string;
  readonly icon: ReactNode;
  readonly keywords: readonly string[];
  readonly action: () => void;
  readonly category: CommandCategory;
}
