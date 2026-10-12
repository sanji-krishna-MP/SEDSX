---
name: codebase-memory
description: >
  Codebase structural knowledge graph and persistent architectural memory.
  Use when exploring codebase architecture, tracing call graphs, locating symbol
  definitions, understanding cross-module dependencies, checking change impacts,
  or navigating multi-language repositories with sub-millisecond graph queries.
argument-hint: "[index|query|trace|architecture|status]"
---

# Codebase Memory (CBM)

High-performance code intelligence engine and knowledge graph for 150+ languages.
Maps functions, classes, imports, call paths, and HTTP routes into a persistent SQLite graph.

## When to Use

- **Always before deep exploration:** Before running brute-force `grep` searches or dumping whole source files into context, query the codebase graph to identify exact target files and functions.
- **Tracing call hierarchies:** Trace inbound and outbound callers (`trace_path`).
- **Architectural overview:** Map high-level subsystem relationships and service boundaries (`get_architecture`).
- **Impact analysis:** Determine what depends on a function/class before modifying or refactoring it.

## Key Operations & Tools

### 1. Indexing
To initialize or refresh the knowledge graph:
- MCP Tool: `index_repository(path=".")`
- CLI: `codebase-memory-mcp cli index_repository path="."`

### 2. Tracing Call Paths
Trace who calls a function (inbound) or what a function calls (outbound):
- MCP Tool: `trace_path(function_name="targetFunction", direction="inbound")`
- MCP Tool: `trace_path(function_name="targetFunction", direction="outbound")`

### 3. Architecture & Structural Exploration
- MCP Tool: `get_architecture()`
- MCP Tool: `get_file_outline(path="src/index.ts")`
- MCP Tool: `get_code_snippet(file_path="...", start_line=..., end_line=...)`

### 4. Graph Querying & Search
- MCP Tool: `search_graph(query="...")`
- MCP Tool: `query_graph(query="...")`
- MCP Tool: `search_code(pattern="...")`

### 5. Visual Graph UI (CBM Lens)
- Web UI available at: `http://localhost:9749`