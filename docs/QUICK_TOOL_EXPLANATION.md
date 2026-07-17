# What the tool does

GraphEval takes a compound question and a trusted context, then splits the question into smaller atomic parts. For each part, it starts from an initial answer fragment, extracts what that answer claims, and checks those claims against a knowledge graph built from the trusted context. Correct claims are kept; wrong or unsupported claims are flagged. The system revises the answer, checks again, and repeats until the part is resolved or it hits a stop condition. Finally it combines the per-part answers into one response. The Research Trace UI shows that loop one question at a time so you can see what was preserved, corrected, and why.

# How the code does it

An LLM handles question decomposition, structured fact extraction from trusted context, claim extraction from answers, and answer revision. Deterministic Python owns normalization, question-target framing, claim-vs-knowledge-graph comparison, SUPPORTED / CONTRADICTED / NO_EVIDENCE labels, stop conditions, and iteration control. The working knowledge graph can gain trusted focused facts from context and derived trusted facts, each with provenance; generated answer claims are compared against that graph but are not automatically trusted or promoted into it. Neo4j can store and visualize base graph facts when enabled, but evaluation happens in Python, not in Neo4j. The frontend Research Trace visualizes the run; it does not change the pipeline.

# 15-second version

GraphEval checks AI answers against a trusted knowledge graph. It splits a compound question into smaller parts, keeps what’s supported, revises what isn’t, and combines the corrected answers. The UI walks you through that process one question at a time.
