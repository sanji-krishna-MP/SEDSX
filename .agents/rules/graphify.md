# Graphify: Codebase & Corpus Knowledge Graph (Always-On)

Always leverage Graphify knowledge graphs for high-level repository mapping and multi-modal understanding:

1. **Fast-Path Querying:**
   - Whenever `graphify-out/graph.json` exists in the project root, treat architectural and relationship questions as Graphify queries (`graphify query "<question>"`).
   - Use detected god nodes and community clusters to understand system boundaries.

2. **Honesty & Integrity:**
   - Maintain the honest audit trail (EXTRACTED, INFERRED, AMBIGUOUS). Never invent connections that cannot be verified in the code or documentation.