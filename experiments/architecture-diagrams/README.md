# Architecture Diagrams

This folder contains Mermaid diagrams to understand how this repository's Agentic RAG differs from traditional fixed-pipeline RAG.

## Suggested reading order

1. 01-traditional-vs-agentic-rag.md
2. 02-main-request-sequence.md
3. 03-tool-loop-activity.md
4. 04-data-and-ingestion-flow.md

## How to preview in VS Code

- Open any file and use Markdown preview.
- Mermaid blocks render directly in preview.

## Why these 4 diagrams

- Comparison sequence: bridges traditional RAG mental model to this codebase.
- Main sequence: end-to-end runtime flow for /api/query.
- Tool-loop activity: isolates the model/tool decision loop.
- Data and ingestion flow: separates indexing/storage concerns from query orchestration.
