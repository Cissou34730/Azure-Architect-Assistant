// Guard for plain objects (records) — rejects arrays, Dates, Maps, Sets, class instances, etc.
// eslint-disable-next-line @typescript-eslint/no-restricted-types -- Type guard input must accept any value
export function isRecord(value: unknown): value is Record<string, unknown> {
  if (typeof value !== "object" || value === null) return false;
  // eslint-disable-next-line @typescript-eslint/no-restricted-types -- Proto can be any value from external source
  const proto: unknown = Object.getPrototypeOf(value);
  return proto === Object.prototype || proto === null;
}
