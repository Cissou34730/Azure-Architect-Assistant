import type { Message } from "../../../types/api";

function serializeKbSources(message: Message): string {
  if (message.kbSources === undefined || message.kbSources.length === 0) {
    return "";
  }

  return message.kbSources
    .map((source) => `${source.url}|${source.title}`)
    .join(";;");
}

function canReuseMessage(
  prevMessage: Message,
  nextMessage: Message,
): boolean {
  if (prevMessage === nextMessage) {
    return true;
  }

  if (prevMessage.id !== nextMessage.id) {
    return false;
  }

  if (prevMessage.role !== nextMessage.role) {
    return false;
  }

  if (prevMessage.content !== nextMessage.content) {
    return false;
  }

  if (prevMessage.timestamp !== nextMessage.timestamp) {
    return false;
  }

  return serializeKbSources(prevMessage) === serializeKbSources(nextMessage);
}

export function reconcileMessages(
  previousMessages: readonly Message[],
  fetchedMessages: readonly Message[],
): readonly Message[] {
  if (previousMessages.length === 0) {
    return fetchedMessages;
  }

  const previousById = new Map(
    previousMessages.map((message) => [message.id, message]),
  );

  return fetchedMessages.map((nextMessage) => {
    const prevMessage = previousById.get(nextMessage.id);
    if (prevMessage !== undefined && canReuseMessage(prevMessage, nextMessage)) {
      return prevMessage;
    }
    return nextMessage;
  });
}

export function findLastNonOptimisticId(
  messages: readonly Message[],
): string | undefined {
  for (let i = messages.length - 1; i >= 0; i--) {
    const id = messages[i].id;
    if (!id.startsWith("opt-")) {
      return id;
    }
  }
  return undefined;
}
