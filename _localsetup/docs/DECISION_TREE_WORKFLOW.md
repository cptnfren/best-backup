---
status: ACTIVE
version: 2.8
---

# Decision tree workflow (reverse prompt)

**Purpose:** AI prompts the user one question at a time with four options (A-D), preferred choice, and rationale. Used to build context before implementation (e.g. PRD/spec clarification). Load skill localsetup-decision-tree-workflow when user invokes it.

## Principle

- Questions are **relevant to the topic**. Goal: **maximum impact context**.
- **One question at a time.** Never dump multiple questions in one turn.

## Format for each question

1. **Setup (optional):** Short statement on topic and why it matters.
2. **Question or decision:** One single question or decision point.
3. **Options:** Four plausible answers labeled **A**, **B**, **C**, **D**.
4. **Preferred option:** State which the AI prefers (e.g. "Preferred: **B**").
5. **Rationale:** One paragraph explaining why that choice is optimal.
6. **User response:** User may pick A/B/C/D, different option, or free-form; use all feedback as context.

## Number of questions

- **Default:** About **7-9 questions** per topic unless user specifies otherwise.
- **Order:** Most important first. User may set a limit (e.g. "no more than 4").

## Flow

- One topic at a time. For each question: output in format above -> wait for answer -> next question or (if done) use answers to update PRD/spec/outcome.

## When to use

- User says: "decision tree", "decision tree workflow", "reverse prompt", "run the decision tree", or similar.
- When clarifying a draft PRD or spec with structured Q&A.

## Checklist

- One question per turn only. Four options (A-D); preferred stated; rationale. Accept A/B/C/D or free-form; use all feedback.

---

<p align="center">
<strong>Author:</strong> <a href="https://github.com/cptnfren">Slavic Kozyuk</a><br>
<strong>Copyright</strong> © 2026 <a href="https://www.cruxexperts.com/">Crux Experts LLC</a> – Innovate, Automate, Dominate.
</p>
