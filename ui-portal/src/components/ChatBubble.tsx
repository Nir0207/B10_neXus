"use client";

import { memo } from "react";
import type { VisualPayload } from "@/services/intelligenceService";
import VisualPayloadChart from "@/components/VisualPayloadChart";

export interface ChatBubbleMessage {
  id: string;
  role: "assistant" | "user";
  text: string;
  sources?: string[];
  visualPayload?: VisualPayload;
}

interface Props {
  message: ChatBubbleMessage;
}

function ChatBubbleComponent({ message }: Props): React.JSX.Element {
  return (
    <div
      className={`rounded-2xl border p-3 ${
        message.role === "assistant"
          ? "bg-surface-container-lowest border-outline-variant/10"
          : "bg-primary/10 border-primary/20"
      }`}
    >
      <p className="text-[11px] leading-relaxed text-on-surface-variant whitespace-pre-wrap">
        {message.text}
      </p>
      {message.visualPayload ? <VisualPayloadChart payload={message.visualPayload} /> : null}
      {message.sources?.length ? (
        <div className="mt-2 flex flex-wrap gap-1">
          {message.sources.map((source) => (
            <span
              className="text-[9px] text-tertiary font-mono bg-tertiary/10 px-1.5 py-0.5 rounded"
              key={source}
            >
              {source}
            </span>
          ))}
        </div>
      ) : null}
    </div>
  );
}

const ChatBubble = memo(ChatBubbleComponent);

export default ChatBubble;
