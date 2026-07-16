import "@testing-library/jest-dom/vitest";

// Node can expose an incomplete experimental localStorage object that shadows
// jsdom inside Vitest workers. Use a deterministic Storage implementation.
const storageValues = new Map<string, string>();
const testLocalStorage: Storage = {
  get length() {
    return storageValues.size;
  },
  clear() {
    storageValues.clear();
  },
  getItem(key: string) {
    return storageValues.get(key) ?? null;
  },
  key(index: number) {
    return [...storageValues.keys()][index] ?? null;
  },
  removeItem(key: string) {
    storageValues.delete(key);
  },
  setItem(key: string, value: string) {
    storageValues.set(key, String(value));
  },
};

Object.defineProperty(globalThis, "localStorage", {
  configurable: true,
  value: testLocalStorage,
});
