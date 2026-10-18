# Evaluation plan

Use this file to report measured results, not guesses. For every live run record date, model ID, prompt version, input, expected behavior, actual output, pass/fail, latency, input/output tokens, estimated cost, and reviewer notes.

## Task 1 — 20 test cases
1. Exact known question returns correct article.
2. Answer includes source URL.
3. Unknown refund policy abstains.
4. Empty question is rejected.
5. Whitespace-only question is rejected.
6. Added article becomes retrievable.
7. Updated article replaces prior content.
8. Feedback is stored.
9. Unknown article ID feedback is rejected.
10. Health endpoint is healthy.
11. Duplicate article URL updates rather than duplicates.
12. Irrelevant article does not become a citation.
13. Retrieved context is bounded.
14. HTML/script-like input is treated as text.
15. Prompt injection inside article is not followed as a system instruction.
16. Missing source results in abstention.
17. Sitemap refresh reports newly added URLs.
18. Sitemap refresh reports removed URLs.
19. Network error during refresh is reported safely.
20. Claude API error is handled without exposing secrets.
21. Image article metadata preserves its source URL.
22. Stale article is not returned after deletion reconciliation.

## Task 2 — 20 test cases
1. How-to email receives a grounded draft.
2. Refund email uses only supported policy.
3. Complaint gets empathetic tone.
4. New project request is categorized as sales/project.
5. Unknown policy triggers human review.
6. Empty email is rejected.
7. Malicious email prompt is treated as untrusted.
8. Draft includes cited source links.
9. Draft does not claim an email was sent.
10. Human edit is stored.
11. Repeated accepted edits are counted by category.
12. Feedback is associated with the draft ID.
13. Approval requires a known draft.
14. Approval changes status only.
15. API unavailable returns a controlled error.
16. Very long email is bounded or rejected.
17. PII is not written to plain logs.
18. Model error leaves draft pending review.
19. Structured output schema is validated.
20. Human override is never overwritten by automated feedback.
21. Duplicate request IDs are handled idempotently.
22. Draft quality can be scored against a labeled example.

## Task 3 — 20 test cases
1. Clear request becomes a requirement.
2. Vague request becomes a clarification question.
3. Existing-product setting is checked against Task 1.
4. Requirements include acceptance criteria.
5. Estimates include assumptions.
6. Estimate has min/likely/max or a documented single estimate.
7. Proposal summarizes scope and exclusions.
8. Second transcript updates prior scope.
9. Added requirement is labeled new.
10. Removed requirement is shown as removed.
11. Out-of-scope change is flagged for extra quote.
12. Conflicting statements are surfaced.
13. Long transcript is handled with bounded chunks.
14. Empty transcript is rejected.
15. Prompt injection inside transcript is ignored.
16. No proposal is sent automatically.
17. Human approval is required.
18. Claude/API failure is surfaced safely.
19. Structured output is validated.
20. Estimate total equals the sum of task estimates.
21. Unknown product capability is marked as an assumption.
22. Senior review is required when confidence is low.

## Metrics
- Grounded answer rate = answers with correct supporting citations / answerable cases.
- Abstention precision = correctly abstained unanswerable cases / all abstentions.
- Unsupported claim rate = unsupported factual claims / factual claims reviewed.
- Human acceptance = drafts accepted without material edit / drafts reviewed.
- Scope coverage = required items captured / expected items in labeled transcript.
- Estimate error = absolute(estimated hours - expert hours) / expert hours.
- Latency = wall-clock seconds from request to response.
- Cost per request = actual input/output tokens multiplied by current model rates.
- Reliability = successful requests / total requests.

## Model comparison protocol
Compare at least two available Claude models or configurations on the same frozen test set. Keep prompts and inputs identical. Report quality, latency, tokens, cost, and failure rate. Do not report unrun results. The `.env.example` model name is only a configurable default; confirm the model is available in your Anthropic Console.
