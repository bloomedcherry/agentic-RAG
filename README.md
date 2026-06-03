# Harness Engineering Agent Demo

This repository contains an enterprise Agentic RAG demo built around an Agent Harness runtime.

## M1: Data And RAG Baseline

Run the first milestone with:

```bash
python -m enterprise_agent.rag.download_raw_data
python -m enterprise_agent.rag.data_builder --min-docs 300
python -m enterprise_agent.rag.build_index
python -m enterprise_agent.rag.retriever --query "差旅报销需要哪些材料" --top-k 5
```

Use the project conda environment:

```bash
/mnt/sdc/zxuny/envs/agent-rag-demo-py310/bin/python -m enterprise_agent.rag.download_raw_data
/mnt/sdc/zxuny/envs/agent-rag-demo-py310/bin/python -m enterprise_agent.rag.data_builder --min-docs 300
/mnt/sdc/zxuny/envs/agent-rag-demo-py310/bin/python -m enterprise_agent.rag.build_index
/mnt/sdc/zxuny/envs/agent-rag-demo-py310/bin/python -m enterprise_agent.rag.retriever --query "差旅报销需要哪些材料" --top-k 5
```

The M1 scope downloads a small set of public Chinese seed documents, expands them into a medium-size enterprise corpus, chunks documents, writes index metadata, and runs top-k retrieval. It supports Markdown, TXT, PDF, DOCX, and HTML parsing. It does not include Planner, Tool Contract, LLM answer generation, Verifier, Retry, or Eval yet.
