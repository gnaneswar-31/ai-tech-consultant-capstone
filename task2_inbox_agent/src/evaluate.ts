
import { readFileSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";
import { EmailSchema, classifyEmail } from "./agent.js";

const datasetPath = resolve("data/emails.json");
const outputPath = resolve("data/evaluation-results.json");

// Expected categories assigned manually for evaluation.
const expectedCategories: Record<string, string> = {
  "email-001": "billing",
  "email-002": "billing",
  "email-003": "billing",
  "email-004": "billing",
  "email-005": "billing",
  "email-006": "support",
  "email-007": "support",
  "email-008": "support",
  "email-009": "support",
  "email-010": "support",
  "email-011": "support",
  "email-012": "support",
  "email-013": "support",
  "email-014": "support",
  "email-015": "support",
  "email-016": "complaint",
  "email-017": "complaint",
  "email-018": "complaint",
  "email-019": "support",
  "email-020": "complaint",
  "email-021": "project_request",
  "email-022": "project_request",
  "email-023": "project_request",
  "email-024": "project_request",
  "email-025": "project_request",
  "email-026": "project_request",
  "email-027": "project_request",
  "email-028": "project_request",
  "email-029": "project_request",
  "email-030": "project_request",
  "email-031": "support",
  "email-032": "support",
  "email-033": "support",
  "email-034": "support",
  "email-035": "support",
  "email-036": "support",
  "email-037": "support",
  "email-038": "support",
  "email-039": "support",
  "email-040": "project_request",
  "email-041": "support",
  "email-042": "billing",
  "email-043": "billing",
  "email-044": "support",
  "email-045": "support",
  "email-046": "support",
  "email-047": "project_request",
  "email-048": "billing",
  "email-049": "support",
  "email-050": "support",
};

type TestEmail = {
  id: string;
  from: string;
  subject: string;
  body: string;
};

const emails = JSON.parse(
  readFileSync(datasetPath, "utf-8")
) as TestEmail[];

const results = emails.map((rawEmail) => {
  const validation = EmailSchema.safeParse(rawEmail);

  if (!validation.success) {
    return {
      email_id: rawEmail.id,
      valid: false,
      expected: expectedCategories[rawEmail.id] ?? null,
      predicted: null,
      correct: false,
      error: validation.error.issues.map((issue) => issue.message).join("; "),
    };
  }

  const email = validation.data;
  const predicted = classifyEmail(email);
  const expected = expectedCategories[email.id] ?? null;

  return {
    email_id: email.id,
    valid: true,
    expected,
    predicted,
    correct: expected !== null && predicted === expected,
    error: null,
  };
});

const validResults = results.filter((result) => result.valid);
const labeledResults = validResults.filter((result) => result.expected !== null);
const correctCount = labeledResults.filter((result) => result.correct).length;
const accuracy = labeledResults.length
  ? (correctCount / labeledResults.length) * 100
  : 0;

writeFileSync(outputPath, JSON.stringify(results, null, 2), "utf-8");

console.log(`Total emails: ${emails.length}`);
console.log(`Valid emails: ${validResults.length}`);
console.log(`Invalid emails: ${emails.length - validResults.length}`);
console.log(`Labeled emails: ${labeledResults.length}`);
console.log(`Correct classifications: ${correctCount}`);
console.log(`Accuracy: ${accuracy.toFixed(2)}%`);

console.log("\nCategory counts:");

for (const category of [
  "billing",
  "support",
  "complaint",
  "project_request",
  "general",
]) {
  const count = validResults.filter(
    (result) => result.predicted === category
  ).length;

  console.log(`${category}: ${count}`);
}

console.log("\nMisclassified emails:");

const mistakes = labeledResults.filter((result) => !result.correct);

if (mistakes.length === 0) {
  console.log("None");
} else {
  for (const result of mistakes) {
    console.log(
      `${result.email_id}: expected=${result.expected}, predicted=${result.predicted}`
    );
  }
}

console.log(`\nResults saved to: ${outputPath}`);
