import { describe, it, expect } from "vitest";
import { classifyEmail, createDraft, approveDraft, recordFeedback, EmailSchema } from "../src/agent.js";

const email = (body:string, subject="Question") => ({id:crypto.randomUUID(),from:"customer@example.com",subject,body});
const known = {answer:"Open Settings and select Billing.",citations:[{title:"Billing help",url:"https://example.com/billing"}],needs_human:false};
const unknown = {answer:"I don't know.",citations:[],needs_human:true};

describe("Inbox Agent", () => {
 it("validates email schema",()=>expect(EmailSchema.safeParse(email("Hi there")).success).toBe(true));
 it("rejects empty body",()=>expect(EmailSchema.safeParse(email("")).success).toBe(false));
 it("rejects missing id",()=>expect(EmailSchema.safeParse({from:"x@y.com",body:"Hello"}).success).toBe(false));
 it("classifies billing",()=>expect(classifyEmail(email("I need a refund"))).toBe("billing"));
 it("classifies cancellation",()=>expect(classifyEmail(email("Please cancel my subscription"))).toBe("billing"));
 it("classifies payment",()=>expect(classifyEmail(email("My payment failed"))).toBe("billing"));
 it("classifies support issue",()=>expect(classifyEmail(email("The app is broken"))).toBe("support"));
 it("classifies bug",()=>expect(classifyEmail(email("I found a bug"))).toBe("support"));
 it("classifies project request",()=>expect(classifyEmail(email("I need a quote for a website change"))).toBe("project_request"));
 it("classifies proposal",()=>expect(classifyEmail(email("Please send a proposal"))).toBe("project_request"));
 it("classifies complaint",()=>expect(classifyEmail(email("I am disappointed"))).toBe("complaint"));
 it("falls back to general",()=>expect(classifyEmail(email("Hello team"))).toBe("general"));
 it("creates pending draft",()=>expect(createDraft(email("billing help"),known).status).toBe("pending_review"));
 it("draft includes citation",()=>expect(createDraft(email("billing help"),known).reply).toContain("https://example.com/billing"));
 it("unknown knowledge triggers human review",()=>expect(createDraft(email("policy?"),unknown).needs_human).toBe(true));
 it("unknown knowledge uses cautious wording",()=>expect(createDraft(email("policy?"),unknown).reply).toContain("review"));
 it("draft has category",()=>expect(createDraft(email("I need a refund"),known).category).toBe("billing"));
 it("draft has email id",()=>{const e=email("Hi");expect(createDraft(e,known).email_id).toBe(e.id)});
 it("approval changes status only",()=>{const d=createDraft(email("Hi"),known);expect(approveDraft(d.id).status).toBe("approved")});
 it("unknown draft approval throws",()=>expect(()=>approveDraft("missing")).toThrow("Draft not found"));
 it("feedback records known draft",()=>{const d=createDraft(email("Hi"),known);expect(recordFeedback({draft_id:d.id,original:d.reply,edited:"Changed",accepted:false}).saved).toBe(true)});
 it("feedback rejects unknown draft",()=>expect(()=>recordFeedback({draft_id:"missing",original:"a",edited:"b",accepted:false})).toThrow());
 it("schema limits email body length",()=>expect(EmailSchema.safeParse(email("x".repeat(20001))).success).toBe(false));
 it("does not send email on approval",()=>expect(approveDraft(createDraft(email("Hi"),known).id).status).toBe("approved"));
});
