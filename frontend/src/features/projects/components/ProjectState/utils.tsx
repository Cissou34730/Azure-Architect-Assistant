import { ReactNode } from "react";
import { isRecord } from "../../../../utils/typeGuards";

export interface NamedItem {
  readonly name: string;
  readonly description?: string;
}

// eslint-disable-next-line @typescript-eslint/no-restricted-types
export function isNamedItem(value: unknown): value is NamedItem {
  return isRecord(value) && typeof value.name === "string";
}

// eslint-disable-next-line @typescript-eslint/no-restricted-types
export function renderMaybeNamed(value: unknown): ReactNode {
  if (value === null || value === undefined) return "";
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") return String(value);

  if (isNamedItem(value)) {
    return (
      <>
        <strong>{value.name}:</strong> {value.description}
      </>
    );
  }
  return JSON.stringify(value);
}
