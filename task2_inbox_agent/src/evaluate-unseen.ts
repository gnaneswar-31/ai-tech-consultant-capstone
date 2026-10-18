
import { readFileSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";
import { EmailSchema, classifyEmail } from "./agent.js";

const inputPath = resolve("data/unseen-emails.json");
const outputPath = resolve("data/unseen-evaluation-results.json");

const expectedCategories: Record<string, string> = {
  "unseen-001": "billing",
  "unseen-002": "support",
  "unseen-003": "project_request",
  "unseen-004": "complaint",
  "unseen-005": "support",
  "unseen-006": "project_request",
  "unseen-007": "billing",
  "unseen-008": "support",
};

const fileContent = readFileSync(inputPath, "utf-8")
  .replace(/^\uFEFF/, "");

const emails = JSON.parse(fileContent) as unknown[];
const results = emails.map((rawEmail) => {
  const validation = EmailSchema.safeParse(rawEmail);

  if (!validation.success) {
    return {
      email_id: "invalid",
      valid: false,
      expected: null,
      predicted: null,
      correct: false,
      error: validation.error.issues
        .map((issue) => issue.message)
        .join("; "),
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
const labeledResults = validResults.filter(
  (result) => result.expected !== null
);
const correctCount = labeledResults.filter(
  (result) => result.correct
).length;

const accuracy = labeledResults.length
  ? (correctCount / labeledResults.length) * 100
  : 0;

writeFileSync(
  outputPath,
  JSON.stringify(results, null, 2),
  "utf-8"
);

console.log(`Unseen emails: ${emails.length}`);
console.log(`Valid emails: ${validResults.length}`);
console.log(`Correct classifications: ${correctCount}`);
console.log(`Accuracy: ${accuracy.toFixed(2)}%`);
console.log("\nIndividual results:");

for (const result of results) {
  console.log(
    `${result.email_id}: expected=${result.expected}, ` +
    `predicted=${result.predicted}, correct=${result.correct}`
  );
}

console.log(`\nResults saved to: ${outputPath}`);
