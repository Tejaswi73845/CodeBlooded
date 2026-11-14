import { evidence, events, people } from "@/data/mock";

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

const personByName = (q: string) =>
  people.find((p) => q.toLowerCase().includes(p.name.toLowerCase().split(" ")[0]));

const evidenceById = (id: string) => evidence.find((e) => e.id === id);

function cite(ids: string[]) {
  return ids.filter((id) => evidenceById(id));
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

export function answer(question: string): AssistantReply {
  const q = question.toLowerCase();
  const person = personByName(question);

  if (q.includes("summar") || q.includes("overview")) {
    return {
      text: `Between 8 and 13 November 2026, a person presenting as vendor onboarding lead **Arjun Mehta** induced Meridian Textiles to transfer **₹18,50,000** to an account held by **Rao Enterprises**.

Four phases stand out:

• **Introduction (8 Nov)** — Contact begins on WhatsApp, framed as a routine bank detail update.
• **Pressure (10 Nov, 22:14)** — A threat message arrives, followed by a spoofed remittance email at 23:02.
• **Diversion (11 Nov, 08:05)** — Two tranches leave the complainant's account.
• **Concealment (11–12 Nov)** — A parking-lot meeting and a device swap reference appear in later evidence.

Confidence is highest on the payment chain (96%) and the shared-device link (92%). The ₹18.5L has not been recovered, and one Telegram export is excluded pending re-export.`,
      citations: cite(["ev-01", "ev-02", "ev-06", "ev-05", "ev-07", "ev-11"]),
    };
  }

  if (q.includes("inconsisten") || q.includes("contradict")) {
    return {
      text: `Three material inconsistencies are recorded in this matter.

• **Contact after 21:00** — Priya Sharma's recorded statement says vendor contact ended before 21:00 on 10 November. The WhatsApp export shows four outgoing messages at **23:41**, three minutes after the threat screenshot. Confidence 96%.
• **Device attribution** — Arjun Mehta and Neha Verma present as separate people, but the same handset identifier appears in both the vendor chat and the Instagram exchange. Confidence 92%.
• **Account provenance** — Vikram Rao says the beneficiary account was opened for a former employee, yet the signature card and the 24 October test transfer indicate otherwise.

The first is directly actionable for disclosure; the second needs a device forensic report before it can be asserted; the third is a lead, not a finding.`,
      citations: cite(["ev-01", "ev-04", "ev-11", "ev-10", "ev-05"]),
    };
  }

  if (q.includes("november 10") || q.includes("nov 10") || q.includes("10 nov")) {
    return {
      text: `**10 November 2026** carries five events across three categories.

• **14:30** — Vendor verification chat initiated (Communication).
• **22:14** — Threat message received and screenshotted (Communication, critical).
• **22:38** — Vikram Rao enters the east corridor on CCTV cam 04 (Physical).
• **23:02** — Spoofed remittance email arrives (Communication).
• **23:41** — Outgoing messages contradict the complainant's statement (Communication).

The 34-minute cluster from 22:14 to 23:41 is the strongest indicator of a rehearsed sequence. Corridor footage and the threat screenshot are both verified; the email header analysis remains at review status.`,
      citations: cite(["ev-02", "ev-03", "ev-06", "ev-01"]),
    };
  }

  if (person) {
    const related = evidence.filter((e) => e.personIds.includes(person.id));
    const relatedEvents = events.filter((e) => e.personIds.includes(person.id));
    return {
      text: `**${person.name}** — ${person.role}, risk ${person.risk}. ${person.note}

${related.length} evidence items and ${relatedEvents.length} timeline events reference this person. Most recent activity: ${relatedEvents[relatedEvents.length - 1]?.title ?? "no recorded events"}.

${related
  .slice(0, 4)
  .map((e) => `• ${e.name} — ${e.status === "processed" ? "processed and verified" : e.status}`)
  .join("\n")}`,
      citations: related.slice(0, 4).map((e) => e.id),
    };
  }

  if (q.includes("chronolog") || q.includes("report") || q.includes("generate")) {
    return {
      text: `Chronological incident report — **EV-2026-0142**

**8 Nov, 09:12** — First information report filed. Scope set for disclosure.
**8 Nov, 14:30** — Vendor verification chat begins on WhatsApp.
**10 Nov, 22:14** — Direct threat received.
**10 Nov, 22:38** — Subject recorded entering the east corridor.
**10 Nov, 23:02** — Spoofed remittance email arrives.
**10 Nov, 23:41** — Chat contradicts the recorded statement.
**11 Nov, 08:05** — ₹18,50,000 transferred in two tranches.
**11 Nov, 17:20** — Three individuals photographed in the parking lot.
**12 Nov, 00:12** — Vehicle returns and is matched by plate.
**12 Nov, 15:44** — Instagram DM references a device swap.
**13 Nov, 10:30** — Subject interview recorded.
**13 Nov, 16:05** — Truncated Telegram export excluded.

The full report builder is ready under **Reports**; the draft includes integrity certificates and supporting evidence references.`,
      citations: cite(["ev-12", "ev-01", "ev-02", "ev-03", "ev-07", "ev-10"]),
    };
  }

  if (q.includes("relationship") || q.includes("connect") || q.includes("network") || q.includes("who")) {
    return {
      text: `The relationship graph currently holds **8 people, 23 connections**.

Three clusters matter:

• **Payment cluster** — Priya Sharma → beneficiary account → Vikram Rao → Dev Patel (registered driver).
• **Device cluster** — Arjun Mehta ↔ Neha Verma via a shared handset identifier; both appear in the 11 Nov parking-lot photograph.
• **Communication cluster** — One WhatsApp thread and one Instagram exchange carry most of the intent evidence.

The bridge between payment and device clusters is the 11 November meeting. That is the highest-value line for interviews.`,
      citations: cite(["ev-13", "ev-11", "ev-05", "ev-01"]),
    };
  }

  if (q.includes("hash") || q.includes("integrity") || q.includes("custody")) {
    return {
      text: `All 14 items carry a **SHA-256** digest recorded at intake and re-verified after processing.

• **13 verified** — hashes match the custody ledger.
• **1 mismatch** — \`Chat_Export_Telegram_Arjun.json\` is truncated at 33 KB; 41% of the message table is missing.
• **0 pending** — the queued parking-lot reel is hashed but still in the recognition queue.

The Telegram export is excluded from findings until a fresh export is preserved and hashed.`,
      citations: cite(["ev-14", "ev-09"]),
    };
  }

  return {
    text: `I can work across all 14 evidence items in this matter. For that question I'd start with the preserved record rather than inference.

Currently the strongest threads are the 10 November threat sequence, the pre-staged beneficiary account, and the shared device between Arjun Mehta and Neha Verma. Ask me to summarize the incident, walk through a specific date, or list everything tied to a person and I'll return the supporting references.`,
    citations: cite(["ev-01", "ev-02", "ev-05"]),
  };
}
