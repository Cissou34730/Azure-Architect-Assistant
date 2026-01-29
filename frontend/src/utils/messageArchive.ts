import { Message } from "../types/api";

const ARCHIVE_KEY_PREFIX = "chat_archive_";
const MAX_IN_MEMORY = 200;

export function archiveOldMessages(
  projectId: string,
  messages: readonly Message[],
): readonly Message[] {
  if (messages.length <= MAX_IN_MEMORY) {
    return messages;
  }

  const toArchive = messages.slice(0, messages.length - MAX_IN_MEMORY);
  const toKeep = messages.slice(-MAX_IN_MEMORY);

  // Archive to sessionStorage
  const archived = getArchivedMessages(projectId);
  const newArchive = [...archived, ...toArchive];

  // Use a map to dedup by id in case of overlaps
  const dedupedMap = new Map<string, Message>();
  newArchive.forEach((msg) => dedupedMap.set(msg.id, msg));
  const finalArchive = Array.from(dedupedMap.values());

  try {
    sessionStorage.setItem(
      `${ARCHIVE_KEY_PREFIX}${projectId}`,
      JSON.stringify(finalArchive),
    );
  } catch (e) {
    console.warn(
      "Failed to archive messages to sessionStorage (likely quota exceeded)",
      e,
    );
  }

  return toKeep;
}

export function getArchivedMessages(projectId: string): readonly Message[] {
  try {
    const stored = sessionStorage.getItem(`${ARCHIVE_KEY_PREFIX}${projectId}`);
    if (stored === null) return [];

    // eslint-disable-next-line @typescript-eslint/no-restricted-types -- JSON parsing boundary
    const parsed: unknown = JSON.parse(stored);

    // eslint-disable-next-line @typescript-eslint/no-restricted-types -- JSON parsing boundary
    function isRecord(value: unknown): value is Record<string, unknown> {
      return typeof value === "object" && value !== null;
    }

    // eslint-disable-next-line @typescript-eslint/no-restricted-types -- JSON parsing boundary
    function isMessageArray(value: unknown): value is readonly Message[] {
      if (!Array.isArray(value)) return false;
      for (const item of value) {
        if (!isRecord(item)) return false;
        if (
          typeof item.id !== "string" ||
          typeof item.projectId !== "string" ||
          typeof item.role !== "string" ||
          typeof item.content !== "string" ||
          typeof item.timestamp !== "string"
        ) {
          return false;
        }
      }
      return true;
    }

    if (isMessageArray(parsed)) return parsed;

    return [];
  } catch (e) {
    console.error("Failed to parse archived messages", e);
    return [];
  }
}

export function clearArchivedMessages(projectId: string): void {
  sessionStorage.removeItem(`${ARCHIVE_KEY_PREFIX}${projectId}`);
}

export function restoreLastBatchFromArchive(
  projectId: string,
  limit = 50,
): { restored: readonly Message[]; remaining: readonly Message[] } {
  const archived = getArchivedMessages(projectId);
  if (archived.length === 0) {
    return { restored: [], remaining: [] };
  }

  const restored = archived.slice(-limit);
  const remaining = archived.slice(0, -limit);

  try {
    if (remaining.length > 0) {
      sessionStorage.setItem(
        `${ARCHIVE_KEY_PREFIX}${projectId}`,
        JSON.stringify(remaining),
      );
    } else {
      clearArchivedMessages(projectId);
    }
  } catch (e) {
    console.warn("Failed to update archive after restoration", e);
  }

  return { restored, remaining };
}
