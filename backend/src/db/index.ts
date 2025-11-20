// Database module - not used in POC (in-memory storage only)
// Keeping this file for backward compatibility

export function initDatabase(): void {
  console.log("✅ Using in-memory storage (no database)");
}

export function closeDatabase(): Promise<void> {
  return Promise.resolve();
}
