// Guard for plain objects (records) — rejects arrays, Dates, Maps, Sets, class instances, etc.
export function isRecord(value: unknown): value is Record<string, unknown> {
  if (typeof value !== "object" || value === null) return false;
  const proto = Object.getPrototypeOf(value);
  return proto === Object.prototype || proto === null;
}
