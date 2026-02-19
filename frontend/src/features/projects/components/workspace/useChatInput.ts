import { useState, useCallback } from "react";

export function useChatInput(
  onSendMessage: (content: string) => Promise<void>,
) {
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);

  const handleSubmit = useCallback(
    async (e: React.SyntheticEvent) => {
      e.preventDefault();
      if (input.trim() === "" || sending) {
        return;
      }

      const message = input.trim();
      setInput("");
      setSending(true);

      try {
        await onSendMessage(message);
      } catch (error) {
        console.error("Failed to send message:", error);
      } finally {
        setSending(false);
      }
    },
    [input, sending, onSendMessage],
  );

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
        void handleSubmit(e);
      }
    },
    [handleSubmit],
  );

  const handleInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      setInput(e.target.value);
    },
    [],
  );

  return {
    input,
    sending,
    handleSubmit,
    handleKeyDown,
    handleInputChange,
  };
}
