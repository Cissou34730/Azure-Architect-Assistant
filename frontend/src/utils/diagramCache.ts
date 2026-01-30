interface CacheEntry {
  svg: string;
  timestamp: number;
}

class DiagramCache {
  private cache = new Map<string, CacheEntry>();
  private readonly maxAge = 1000 * 60 * 60; // 1 hour

  get(key: string): string | null {
    const entry = this.cache.get(key);
    if (entry === undefined) return null;

    // Check if expired
    if (Date.now() - entry.timestamp > this.maxAge) {
      this.cache.delete(key);
      return null;
    }

    return entry.svg;
  }

  set(key: string, svg: string): void {
    this.cache.set(key, {
      svg,
      timestamp: Date.now(),
    });

    // Prevent cache from growing indefinitely (limit to 50 items)
    if (this.cache.size > 50) {
      const firstKey = this.cache.keys().next().value;
      if (typeof firstKey === "string") {
        this.cache.delete(firstKey);
      }
    }
  }

  invalidate(key: string): void {
    this.cache.delete(key);
  }

  clear(): void {
    this.cache.clear();
  }

  size(): number {
    return this.cache.size;
  }
}

export const diagramCache = new DiagramCache();
