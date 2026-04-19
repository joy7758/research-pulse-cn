# Zotero Reference Strategy v1

## Position
- Zotero is a reference point for product ideas, not a source-code base for this repository.
- This commercial product must not fork Zotero.
- This commercial product must not copy Zotero source code.
- This product must not use Zotero branding or present itself as “Zotero China”.

## Product Concepts Worth Studying
- Item
- Collection
- Tag
- Attachment
- Note
- Annotation
- Connector / translator
- Group library

## Clean-Room Implementation Approach
- Study concepts and user workflows only.
- Rephrase product behavior in repository-owned language and models.
- Implement parsers, data models, and UI flows from scratch inside this codebase.
- Keep internal naming, storage, and service boundaries product-owned and production-ready.

## Compatibility Strategy
- Prefer open export/import formats first:
  - CSL JSON
  - BibTeX
  - RIS
  - EndNote XML
- Consider later compatibility layers only after the MVP import pipeline is stable:
  - Zotero RDF
  - Better BibTeX export

## China-First Import Paths
- PDF folder import
- Excel import
- CNKI export later
- Wanfang export later
- VIP export later
- NoteExpress migration later
- EndNote migration later

## Why Not A Zotero Fork
- A fork would drag the product into code ownership, licensing, maintenance, and branding risk that does not help the current MVP.
- The current product needs a China-first import-progress-pulse workflow, not a clone of a mature reference manager.
- A clean-room path keeps the architecture aligned with this repository's pulse engine, desktop shell, official-account path, and mini-program path.

## Legal Boundary Note
- Do not copy Zotero source code.
- Do not use Zotero trademarks in product naming or marketing.
- Consult legal counsel before any source-level reuse discussion.
