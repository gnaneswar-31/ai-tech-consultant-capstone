
import { z } from "zod";
import {
  existsSync,
  mkdirSync,
  readFileSync,
  writeFileSync,
} from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

export const EmailSchema = z.object({
  id: z.string().min(1),
  from: z.string().min(3).max(320),
  subject: z.string().max(500).default(""),
  body: z.string().min(2).max(20000),
});

export type EmailInput = z.infer<typeof EmailSchema>;

export type KnowledgeResult = {
  answer: string;
  citations: { title: string; url: string }[];
  needs_human: boolean;
};

export type Draft = {
  id: string;
  email_id: string;
  category: string;
  reply: string;
  citations: { title: string; url: string }[];
  status: "pending_review" | "approved";
  needs_human: boolean;
};

type FeedbackEntry = {
  draft_id: string;
  category: string;
  original: string;
  edited: string;
  accepted: boolean;
};

type SendHistoryEntry = {
  draft_id: string;
  category: string;
  sent_unchanged: boolean;
  sent_at: string;
};

const drafts = new Map<string, Draft>();

const currentDir = dirname(fileURLToPath(import.meta.url));
const dataDir = resolve(currentDir, "../data");
const feedbackPath = resolve(dataDir, "feedback.json");
const sendHistoryPath = resolve(dataDir, "send-history.json");

function loadJsonArray<T>(
  path: string,
  isValid: (item: unknown) => item is T
): T[] {
  try {
    if (!existsSync(path)) return [];

    const saved: unknown = JSON.parse(readFileSync(path, "utf-8"));
    if (!Array.isArray(saved)) return [];

    return saved.filter(isValid);
  } catch (error) {
    console.error(`Could not load ${path}:`, error);
    return [];
  }
}

function isFeedbackEntry(item: unknown): item is FeedbackEntry {
  if (!item || typeof item !== "object") return false;

  const entry = item as Record<string, unknown>;
  return (
    typeof entry.draft_id === "string" &&
    typeof entry.original === "string" &&
    typeof entry.edited === "string" &&
    typeof entry.accepted === "boolean" &&
    typeof entry.category === "string"
  );
}

function isSendHistoryEntry(item: unknown): item is SendHistoryEntry {
  if (!item || typeof item !== "object") return false;

  const entry = item as Record<string, unknown>;
  return (
    typeof entry.draft_id === "string" &&
    typeof entry.category === "string" &&
    entry.sent_unchanged === true &&
    typeof entry.sent_at === "string"
  );
}

const feedback: FeedbackEntry[] = loadJsonArray(
  feedbackPath,
  isFeedbackEntry
);

const sendHistory: SendHistoryEntry[] = loadJsonArray(
  sendHistoryPath,
  isSendHistoryEntry
);

function saveJson(path: string, data: unknown): void {
  mkdirSync(dataDir, { recursive: true });
  writeFileSync(path, JSON.stringify(data, null, 2), "utf-8");
}

function findLearnedReply(category: string): string | undefined {
  const latest = [...feedback]
    .reverse()
    .find(
      (entry) =>
        entry.accepted &&
        entry.category === category &&
        entry.edited.trim().length > 0
    );

  return latest?.edited;
}


export function classifyEmail(email: EmailInput): string {
  const text = `${email.subject} ${email.body}`.toLowerCase();

  // 1. Billing and payment-related emails
  if (
    /\b(refund|cancel|cancellation|charge|billing|payment|invoice|subscription|discount|renew|price|charged|card|overcharged)\b/.test(text)
  ) {
    return "billing";
  }

  // 2. Complaints should be recognized before general support issues
  if (
    /\b(complaint|unhappy|disappointed|poor service|unresolved|escalate|manager|not satisfied|frustrating|frustrated)\b/.test(text) ||
    text.includes("nobody has resolved") ||
    text.includes("several times")
  ) {
    return "complaint";
  }

  // 3. Technical support issues take priority over feature requests.
  // This prevents performance problems from being classified as projects.
  if (
    /\b(bug|error|not working|broken|issue|cannot log in|can't log in|login|password|upload|slow|performance|takes too long|load time|loading|images|contact form|mobile layout|browser compatibility|publish page|security|secure my account|unauthorized access|accessed without permission|account access|account details changed|unexpected website change|support ticket|support hours|data retention|domain configuration|data recovery|missing|outage|website unavailable|feature availability|documentation|delete account)\b/.test(text) ||
    text.includes("returns no results") ||
    text.includes("takes almost a minute") ||
    text.includes("performance issue") ||
    text.includes("forgot my password")
  ) {
    return "support";
  }

  // 4. New projects, requested features, proposals and meetings
  if (
    /\b(quote|quotation|proposal|new project|redesign|booking functionality|booking portal|customer booking|e-commerce|migration|integration|accessibility improvements|project timeline|project scope|custom feature|meeting request|meeting|add a blog|blog section|feature request|new feature|add an option|download reports|excel files|export reports|estimated cost|website design|build a|develop a|create a feature|new functionality)\b/.test(text) ||
    text.includes("want to build") ||
    text.includes("build a customer booking portal") ||
    text.includes("download their reports as excel files") ||
    text.includes("discuss the new website") ||
    text.includes("project scope, timeline")
  ) {
    return "project_request";
  }

  return "general";
}

export function createDraft(
  emailRaw: unknown,
  knowledge: KnowledgeResult
): Draft {
  const email = EmailSchema.parse(emailRaw);
  const category = classifyEmail(email);
  const grounded =
    !knowledge.needs_human && knowledge.answer.trim().length > 0;

  const learnedReply = findLearnedReply(category);

  let reply: string;

  if (grounded) {
    reply = `Hello,

Thank you for contacting us. ${knowledge.answer}

${
  knowledge.citations.length
    ? "Reference: " +
      knowledge.citations.map((citation) => citation.url).join(", ") +
      "\n\n"
    : ""
}Please let us know if you need anything else.

Regards,
Support Team`;
  } else if (learnedReply) {
    reply = learnedReply;
  } else {
    reply = `Hello,

Thank you for contacting us. I want to make sure we give you the correct information, so a team member will review your request before we confirm any details.

Regards,
Support Team`;
  }

  const draft: Draft = {
    id: crypto.randomUUID(),
    email_id: email.id,
    category,
    reply,
    citations: knowledge.citations,
    status: "pending_review",
    needs_human: !grounded,
  };

  drafts.set(draft.id, draft);
  return draft;
}

export function getDraft(id: string): Draft | undefined {
  return drafts.get(id);
}

export function approveDraft(id: string): Draft {
  const draft = drafts.get(id);
  if (!draft) throw new Error("Draft not found");

  draft.status = "approved";
  drafts.set(id, draft);

  // Approval does not mean the email was sent.
  return draft;
}

export function recordFeedback(input: {
  draft_id: string;
  original: string;
  edited: string;
  accepted: boolean;
}) {
  const draft = drafts.get(input.draft_id);
  if (!draft) throw new Error("Draft not found");

  const entry: FeedbackEntry = {
    ...input,
    category: draft.category,
  };

  feedback.push(entry);

  try {
    saveJson(feedbackPath, feedback);
  } catch (error) {
    feedback.pop();
    console.error("Could not save feedback:", error);
    throw new Error("Could not save feedback to disk");
  }

  return { saved: true, count: feedback.length };
}

// Call only after an email provider confirms a successful send.
export function recordSuccessfulSend(
  draftId: string,
  sentReply: string
) {
  const draft = drafts.get(draftId);
  if (!draft) throw new Error("Draft not found");

  if (draft.status !== "approved") {
    throw new Error("Draft must be approved before sending");
  }

  if (sentReply !== draft.reply) {
    return {
      recorded: false,
      reason: "Reply was changed before sending",
    };
  }

  if (sendHistory.some((entry) => entry.draft_id === draftId)) {
    return {
      recorded: false,
      reason: "This draft has already been recorded",
    };
  }

  const entry: SendHistoryEntry = {
    draft_id: draftId,
    category: draft.category,
    sent_unchanged: true,
    sent_at: new Date().toISOString(),
  };

  sendHistory.push(entry);

  try {
    saveJson(sendHistoryPath, sendHistory);
  } catch (error) {
    sendHistory.pop();
    console.error("Could not save send history:", error);
    throw new Error("Could not save send history");
  }

  return {
    recorded: true,
    unchangedSendCount: getUnchangedSendCount(draft.category),
    canAutoSend: canAutoSend(draft.category),
  };
}

export function getUnchangedSendCount(category: string): number {
  return sendHistory.filter(
    (entry) =>
      entry.category === category &&
      entry.sent_unchanged
  ).length;
}

export function canAutoSend(category: string): boolean {
  return getUnchangedSendCount(category) >= 20;
}

export function feedbackCount(): number {
  return feedback.length;
}
