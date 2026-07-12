# Capability Layer

Reusable skills that compose Knowledge, Decision, and Memory — never duplicate orchestration.

## Skills (16)

| Skill ID | Name |
|----------|------|
| `deep-research` | Deep Research |
| `company-research` | Company Research |
| `product-research` | Product Research |
| `document-summarisation` | Document Summarisation |
| `specification-generation` | Specification Generation |
| `email-drafting` | Email Drafting |
| `meeting-preparation` | Meeting Preparation |
| `task-planning` | Task Planning |
| `github-repository-analysis` | GitHub Repository Analysis |
| `code-review` | Code Review |
| `travel-planning` | Travel Planning |
| `flight-research` | Flight Research |
| `hotel-research` | Hotel Research |
| `web-research` | Web Research |
| `financial-comparison` | Financial Comparison |
| `decision-brief-generation` | Decision Brief Generation |

## Usage

```bash
ai-os skill list
ai-os skill show deep-research
ai-os skill run email-drafting --input '{"topic":"Project update","recipient":"team"}'
```

Skills auto-register as Agent Runtime tools (`skill_*`) during `discover_tools()`.
