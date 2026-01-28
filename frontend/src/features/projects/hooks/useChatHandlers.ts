import { useToast } from "../../../hooks/useToast";
import { SendMessageResponse } from "../../../types/api";

interface UseChatHandlersProps {
  readonly chatInput: string;
  readonly sendMessage: (msg: string) => Promise<SendMessageResponse>;
}

export function useChatHandlers({
  chatInput,
  sendMessage,
}: UseChatHandlersProps) {
  const { error: showError } = useToast();

  const handleSendChatMessage = async (e?: React.FormEvent): Promise<void> => {
    e?.preventDefault();
    if (chatInput.trim() === "") {
      return;
    }

    try {
      await sendMessage(chatInput);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Chat failed";
      showError(`Error: ${msg}`);
    }
  };

  return { handleSendChatMessage };
}
