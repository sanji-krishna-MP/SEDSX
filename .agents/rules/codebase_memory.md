# Codebase Memory: Structural Graph-First Navigation (Always-On)

Always prioritize structural knowledge graph queries over brute-force file scanning:

1. **Graph-First Exploration:**
   - Before running broad greps or reading large files into context, query the codebase memory graph (`trace_path`, `query_graph`, `search_graph`, `get_architecture`).
   - Use `index_repository(path=".")` when operating in an unindexed or updated codebase.

2. **Call Hierarchy & Impact:**
   - Trace inbound and outbound callers (`trace_path`) before refactoring or modifying shared symbols.
   - Check cross-module dependencies to prevent unintended regressions.

3. **Token Efficiency:**
   - Target precise function signatures and snippets (`get_code_snippet`, `get_file_outline`) rather than dumping full files into context.