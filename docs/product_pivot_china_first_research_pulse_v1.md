# Product Pivot: China-First Research Pulse v1

## Why The Project Is Pivoting
- The repository accumulated too much energy on internal admin tooling polish.
- That work was real, but it drifted away from the product question that matters most:
  - how a China-first research user imports papers
  - how that user tracks progress
  - how the system generates a useful daily Research Pulse
  - how the pulse reaches the user through desktop, official account, and mini-program
- The product now needs direction clarity more than another layer of admin preset refinement.

## What Went Wrong With Overbuilding Admin Tooling
- The project kept extending the same browser-local admin preset surface:
  - saved views
  - preset workspace
  - health score
  - threshold preferences
  - report export
  - clipboard summaries
- Each phase was internally coherent, but the sequence over-optimized operator convenience instead of user value.
- The cost of that drift:
  - roadmap attention moved away from paper import and paper progress
  - MVP delivery paths became harder to see
  - the repository risked looking like an admin shell project instead of a research product

## Product Positioning
- One-sentence positioning:
  - Research Pulse CN is a China-first research paper management and daily pulse system that helps users import papers, track progress, and receive daily research updates through desktop, official account, and mini-program surfaces.

## Target Users In China
- Graduate students
- PhD students
- Supervisors
- Research assistants
- Editors
- Research organizations

## Core Workflow
1. Import papers.
2. Track paper and research progress.
3. Generate a daily Research Pulse.
4. Deliver that pulse through desktop, official account, and mini-program surfaces.

## What Remains Useful From The Existing System
- Pulse engine
- Digest orchestration
- Official-account delivery path
- Mini-program reading path
- Desktop client foundation
- External retrieval planning and execution

## What Is Frozen
- Group-workspace admin registry preset work
- Local preset health score extensions
- Threshold, report, print, export, copy, and audit extensions on that same track
- Share-registry UX embellishment beyond blocker fixes

## What Frozen Means In Practice
- Keep existing code.
- Fix blockers only if they prevent the pivot path.
- Do not plan new feature phases on top of the admin preset/report track.
- Do not treat the admin preset system as the current product center.

## What The Next MVP Should Do
- Accept practical paper imports first.
- Make imported papers visible and editable in a clear progress workbench.
- Feed those imported papers into the existing pulse pipeline.
- Deliver a daily summary through already valuable delivery surfaces:
  - desktop
  - official account
  - mini-program
- Delay advanced integrations until the import-progress-pulse loop is working end to end.
