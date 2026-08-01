---
name: deep-research
description: Runtime methodology for plan-execute research agents. Use when a task requires multi-source research, evidence-driven investigation, follow-up evidence collection, and auditable claim-evidence reporting.
---

# Deep Research Runtime Skill

## Goal

Run research as a productized workflow: plan evidence needs, execute tools, identify gaps, perform second-round supplementation, then synthesize business conclusions.

## Workflow

1. Identify task type and subject boundary.
2. Load domain skill and fixed report outline.
3. Create evidence plan by chapter.
4. Execute tools by evidence need.
5. Build claims only from available evidence or cautious inference.
6. Reflect gaps and run second-round supplementation when valuable.
7. Synthesize a report for the business reader.
8. Move research process, tool traces, and raw claim-evidence details to appendix.

## Planning Rules

- Plan must be actionable by tools.
- Avoid vague tasks like “分析风险”.
- Prefer “核查是否存在影响授信准入的重大诉讼、被执行、失信、行政处罚或监管问询”.
- Each task must specify required evidence, preferred tools, success criteria, and fallback language.
- If a source is unavailable, route to alternative sources and record the data boundary.

## Evidence Rules

- Distinguish official/authorized data, customer uploaded files, listed company announcements, internal knowledge, public search clues, and LLM inference.
- Public search can support “线索/疑似/需复核”, not definitive negative conclusions.
- Evidence gaps must become follow-up questions or business actions, not generic disclaimers.

## Report Rules

- Report page is not the research log.
- Main report order: conclusion -> risk judgment -> credit action -> supporting basis.
- Show evidence as “查看依据”; keep full source details in appendix.
- Use claim-evidence appendix for auditors, not as the main business reading flow.

