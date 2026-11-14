import { api } from "@/lib/api";

export interface AssistantReply {
  text: string;
  citations: string[];
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  text: string;
  citations?: string[];
}

export function suggestedPrompts() {
  return [
    "Summarize this incident.",
    "What happened on November 10?",
    "Show all evidence involving Arjun Mehta.",
    "Identify inconsistencies between conversations.",
    "Generate a chronological incident report.",
  ];
}

/**
 * Ask the real evidence-grounded assistant (FastAPI POST /api/assistant/chat).
 * Citations carry the source evidence names returned by the backend.
 */
export async function answer(question: string): Promise<AssistantReply> {
  const result = await api.chat(question);
  let text = result.answer;
  if (result.limitations.length > 0) {
    text += "\n\nLimitations:\n" + result.limitations.map((limitation) => `• ${limitation}`).join("\n");
  }
  return {
    text,
    citations: [...new Set(result.sources.map((source) => source.evidenceName))],
  };
}
