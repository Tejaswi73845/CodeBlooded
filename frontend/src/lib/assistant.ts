import { api } from "@/lib/api";

export interface AssistantSource {
  evidenceId: string;
  name: string;
  fileType: string;
  excerpt: string;
  locator?: string | null;
  relevance: number;
}

export interface AssistantReply {
  text: string;
  citations: string[];
  sources: AssistantSource[];
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  text: string;
  citations?: string[];
  sources?: AssistantSource[];
}

export function suggestedPrompts() {
  return [
    "Summarize the preserved evidence.",
    "What happened on the most recent dated event?",
    "Which people or places are connected?",
    "Identify inconsistencies between sources.",
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
    sources: result.sources.map((source) => ({
      evidenceId: source.evidenceId,
      name: source.evidenceName,
      fileType: source.fileType,
      excerpt: source.excerpt,
      locator: source.locator,
      relevance: source.relevance,
    })),
  };
}
