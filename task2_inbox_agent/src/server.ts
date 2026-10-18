
import express from "express";
import {
  EmailSchema,
  createDraft,
  approveDraft,
  recordFeedback,
  feedbackCount,
} from "./agent.js";

const app = express();

app.use(express.json({ limit: "256kb" }));

const knowledgeUrl =
  process.env.KNOWLEDGE_API_URL ?? "http://127.0.0.1:8000";

// Health check
app.get("/health", (_req, res) => {
  res.json({ status: "ok" });
});

// Check the number of feedback entries loaded from disk
app.get("/feedback/count", (_req, res) => {
  res.json({ count: feedbackCount() });
});

// Create an email reply draft using the Knowledge Brain
app.post("/draft", async (req, res) => {
  const parsed = EmailSchema.safeParse(req.body);

  if (!parsed.success) {
    return res.status(422).json({
      error: "Invalid email input",
      details: parsed.error.flatten(),
    });
  }

  try {
    const response = await fetch(`${knowledgeUrl}/ask`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        question: `${parsed.data.subject}\n${parsed.data.body}`,
      }),
      signal: AbortSignal.timeout(8000),
    });

    if (!response.ok) {
      return res.status(502).json({
        error: "Knowledge Brain unavailable; draft not created",
      });
    }

    const knowledge = (await response.json()) as {
      answer: string;
      citations: { title: string; url: string }[];
      needs_human: boolean;
    };

    return res.json(createDraft(parsed.data, knowledge));
  } catch {
    return res.status(502).json({
      error: "Could not contact Knowledge Brain; draft not created",
    });
  }
});

// Record human feedback on an existing draft
app.post("/feedback", (req, res) => {
  const { draft_id, original, edited, accepted } = req.body ?? {};

  if (
    typeof draft_id !== "string" ||
    typeof original !== "string" ||
    typeof edited !== "string" ||
    typeof accepted !== "boolean"
  ) {
    return res.status(422).json({
      error:
        "draft_id and original must be strings, edited must be a string, and accepted must be a boolean",
    });
  }

  try {
    return res.json(
      recordFeedback({ draft_id, original, edited, accepted }),
    );
  } catch (error) {
    if (
      error instanceof Error &&
      error.message === "Could not save feedback to disk"
    ) {
      return res.status(500).json({ error: error.message });
    }

    return res.status(404).json({ error: "Draft not found" });
  }
});

// Approve a draft; this does not send an email
app.post("/approve", (req, res) => {
  try {
    return res.json(approveDraft(String(req.body?.draft_id ?? "")));
  } catch {
    return res.status(404).json({ error: "Draft not found" });
  }
});

const port = Number(process.env.PORT ?? 3000);

app.listen(port, () => {
  console.log(`Inbox Agent listening on http://127.0.0.1:${port}`);
});
