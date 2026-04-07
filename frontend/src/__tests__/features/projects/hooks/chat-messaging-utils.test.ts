import { describe, it, expect } from "vitest";
import {
  reconcileMessages,
  findLastNonOptimisticId,
} from "../../../../features/projects/hooks/chat-messaging-utils";
import type { Message } from "../../../../features/knowledge/types/api-kb";

const msg = (
  id: string,
  content: string,
  role: "user" | "assistant" = "user",
): Message => ({
  id,
  projectId: "p1",
  role,
  content,
  timestamp: "2025-01-01T00:00:00Z",
});

describe("reconcileMessages", () => {
  it("returns fetched when previous is empty", () => {
    const fetched = [msg("1", "hi")];
    const result = reconcileMessages([], fetched);
    expect(result).toBe(fetched);
  });

  it("reuses previous object identity when content matches", () => {
    const prev = [msg("1", "hi")];
    const fetched = [msg("1", "hi")];
    const result = reconcileMessages(prev, fetched);
    expect(result[0]).toBe(prev[0]);
  });

  it("returns new object when content differs", () => {
    const prev = [msg("1", "hi")];
    const fetched = [msg("1", "updated")];
    const result = reconcileMessages(prev, fetched);
    expect(result[0]).toBe(fetched[0]);
    expect(result[0]).not.toBe(prev[0]);
  });

  it("returns new object when role differs", () => {
    const prev = [msg("1", "hi", "user")];
    const fetched = [msg("1", "hi", "assistant")];
    const result = reconcileMessages(prev, fetched);
    expect(result[0]).toBe(fetched[0]);
  });

  it("handles kbSources differences", () => {
    const prev = [{ ...msg("1", "hi"), kbSources: [{ url: "a", title: "A", section: "", score: 1 }] }];
    const fetched = [{ ...msg("1", "hi"), kbSources: [{ url: "b", title: "B", section: "", score: 1 }] }];
    const result = reconcileMessages(prev, fetched);
    expect(result[0]).toBe(fetched[0]);
  });

  it("reuses when kbSources match", () => {
    const sources = [{ url: "a", title: "A", section: "", score: 1 }];
    const prev = [{ ...msg("1", "hi"), kbSources: sources }];
    const fetched = [{ ...msg("1", "hi"), kbSources: [{ url: "a", title: "A", section: "", score: 1 }] }];
    const result = reconcileMessages(prev, fetched);
    expect(result[0]).toBe(prev[0]);
  });

  it("handles mixed reuse and new messages", () => {
    const prev = [msg("1", "hi"), msg("2", "there")];
    const fetched = [msg("1", "hi"), msg("2", "changed"), msg("3", "new")];
    const result = reconcileMessages(prev, fetched);
    expect(result[0]).toBe(prev[0]); // reused
    expect(result[1]).toBe(fetched[1]); // changed
    expect(result[2]).toBe(fetched[2]); // new
  });
});

describe("findLastNonOptimisticId", () => {
  it("returns undefined for empty array", () => {
    expect(findLastNonOptimisticId([])).toBeUndefined();
  });

  it("returns undefined when all optimistic", () => {
    const messages = [msg("opt-1", "a"), msg("opt-2", "b")];
    expect(findLastNonOptimisticId(messages)).toBeUndefined();
  });

  it("returns last non-optimistic id", () => {
    const messages = [msg("1", "a"), msg("2", "b"), msg("opt-3", "c")];
    expect(findLastNonOptimisticId(messages)).toBe("2");
  });

  it("returns the very last id when none are optimistic", () => {
    const messages = [msg("1", "a"), msg("2", "b")];
    expect(findLastNonOptimisticId(messages)).toBe("2");
  });
});
