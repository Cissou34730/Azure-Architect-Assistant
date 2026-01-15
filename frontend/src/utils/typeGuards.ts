// eslint-disable-next-line @typescript-eslint/no-restricted-types
export function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}
