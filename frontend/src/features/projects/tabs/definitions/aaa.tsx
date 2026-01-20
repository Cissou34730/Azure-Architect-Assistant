import { ProjectTab } from "../types";
import { AaaTabAdapter } from "../adapters/AaaTabAdapter";

export const aaaTab: ProjectTab = {
  id: "aaa",
  label: "AAA",
  path: "aaa",
  component: AaaTabAdapter,
};
