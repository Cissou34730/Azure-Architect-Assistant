/* eslint-disable @typescript-eslint/no-unsafe-type-assertion */
/* eslint-disable @typescript-eslint/no-unnecessary-type-parameters */
/* eslint-disable @typescript-eslint/no-restricted-types */
import { isRecord } from "./typeGuards";

/**
 * Utility to map between snake_case (Backend) and camelCase (Frontend)
 */

export function toCamel(str: string): string {
  return str.replace(/([-_][a-z])/gi, (match) => {
    return match.toUpperCase().replace("-", "").replace("_", "");
  });
}

export function keysToCamel<T>(obj: unknown): T {
  if (Array.isArray(obj)) {
    // eslint-disable-next-line no-restricted-syntax
    return obj.map((v: unknown) => keysToCamel(v)) as T;
  }
  if (isRecord(obj) && !(obj instanceof Date) && !(obj instanceof File)) {
    const result: Record<string, unknown> = {};
    for (const key of Object.keys(obj)) {
      const camelKey = toCamel(key);
      result[camelKey] = keysToCamel(obj[key]);
    }
    // eslint-disable-next-line no-restricted-syntax
    return result as T;
  }
  // eslint-disable-next-line no-restricted-syntax
  return obj as T;
}

export function toSnake(str: string): string {
  return str.replace(/[A-Z]/g, (letter) => `_${letter.toLowerCase()}`);
}

export function keysToSnake<T>(obj: unknown): T {
  if (Array.isArray(obj)) {
    // eslint-disable-next-line no-restricted-syntax
    return obj.map((v: unknown) => keysToSnake(v)) as T;
  }
  if (isRecord(obj) && !(obj instanceof Date) && !(obj instanceof File)) {
    const result: Record<string, unknown> = {};
    for (const key of Object.keys(obj)) {
      const snakeKey = toSnake(key);
      result[snakeKey] = keysToSnake(obj[key]);
    }
    // eslint-disable-next-line no-restricted-syntax
    return result as T;
  }
  // eslint-disable-next-line no-restricted-syntax
  return obj as T;
}
