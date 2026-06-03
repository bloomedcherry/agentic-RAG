#!/usr/bin/env bash
set -euo pipefail

export HTTP_PROXY=http://127.0.0.1:27890
export HTTPS_PROXY=http://127.0.0.1:27890
export ALL_PROXY=socks5://127.0.0.1:27890
export http_proxy=http://127.0.0.1:27890
export https_proxy=http://127.0.0.1:27890
export all_proxy=socks5://127.0.0.1:27890

export CONDA_PKGS_DIRS=/mnt/sdc/zxuny/tmp/conda-pkgs
export PIP_CACHE_DIR=/mnt/sdc/zxuny/tmp/pip-cache
export TMPDIR=/mnt/sdc/zxuny/tmp
export TMP=/mnt/sdc/zxuny/tmp
export TEMP=/mnt/sdc/zxuny/tmp
export PIP_INDEX_URL=https://pypi.org/simple
export PIP_CONFIG_FILE=/dev/null
export PIP_DISABLE_PIP_VERSION_CHECK=1
export PYTHONNOUSERSITE=1

ENV_PREFIX=/mnt/sdc/zxuny/envs/agent-rag-demo-py310
PROJECT_DIR=/mnt/sdc/zxuny/github/harness-engineering

mkdir -p "$CONDA_PKGS_DIRS" "$PIP_CACHE_DIR" "$TMPDIR"

cd "$PROJECT_DIR"

echo "[START] $(date)"
echo "[ENV] $ENV_PREFIX"
echo "[CONDA] $(conda --version)"
echo "[YAML] $PROJECT_DIR/environment.yml"

conda create \
  -p "$ENV_PREFIX" \
  -c defaults \
  --override-channels \
  python=3.10 \
  pip \
  setuptools \
  wheel \
  sqlite \
  -y

PYTHON="$ENV_PREFIX/bin/python"

echo "[PIP] upgrade build tooling"
"$PYTHON" -m pip install --upgrade pip setuptools wheel

echo "[PIP] base compatibility"
"$PYTHON" -m pip install \
  typing-extensions==4.12.2 \
  numpy==1.26.4 \
  scipy==1.13.1

echo "[PIP] CPU torch from official PyTorch index"
"$PYTHON" -m pip install \
  --index-url https://download.pytorch.org/whl/cpu \
  torch==2.5.1+cpu

echo "[PIP] web/api"
"$PYTHON" -m pip install \
  fastapi==0.115.8 \
  "uvicorn[standard]==0.34.3" \
  streamlit==1.41.1 \
  pydantic==2.10.6 \
  pydantic-settings==2.7.1 \
  python-dotenv==1.0.1 \
  python-multipart==0.0.20

echo "[PIP] agent"
"$PYTHON" -m pip install \
  langgraph==1.1.0 \
  "langchain-core>=1.3.3,<1.4.0" \
  "openai>=1.59.9,<2.0.0" \
  "tenacity>=8.5.0,<10.0.0"

echo "[PIP] rag"
"$PYTHON" -m pip install \
  sentence-transformers==3.3.1 \
  transformers==4.48.3 \
  faiss-cpu==1.9.0.post1 \
  rank-bm25==0.2.2 \
  pypdf==5.1.0 \
  python-docx==1.1.2 \
  pandas==2.2.3 \
  openpyxl==3.1.5 \
  beautifulsoup4==4.12.3 \
  markdown==3.7

echo "[PIP] db/eval/trace/security"
"$PYTHON" -m pip install \
  sqlalchemy==2.0.36 \
  pytest==8.3.4 \
  jsonlines==4.0.0 \
  loguru==0.7.3 \
  rich==13.9.4 \
  scikit-learn==1.5.2 \
  tqdm==4.67.1 \
  "python-jose[cryptography]==3.3.0" \
  "passlib[bcrypt]==1.7.4" \
  bcrypt==4.2.1

echo "[PIP] final compatibility pins"
"$PYTHON" -m pip install \
  langchain-protocol==0.0.10 \
  cryptography==44.0.3 \
  typing-extensions==4.12.2 \
  tqdm==4.67.1 \
  scikit-learn==1.5.2 \
  pandas==2.2.3

echo "[PIP CHECK]"
"$PYTHON" -m pip check

echo "[VERIFY IMPORTS]"
"$PYTHON" - <<'PY'
import sys
from importlib.metadata import version

import torch
import numpy as np
import faiss
from fastapi import FastAPI
from pydantic import BaseModel
from sqlalchemy import create_engine, text
from rank_bm25 import BM25Okapi
from langgraph.graph import START, END, StateGraph
from typing_extensions import TypedDict

pkgs = [
    "typing-extensions", "torch", "fastapi", "streamlit", "pydantic",
    "langgraph", "langchain-core", "openai", "sentence-transformers",
    "transformers", "faiss-cpu", "sqlalchemy", "numpy", "scikit-learn",
]
for package in pkgs:
    print(f"{package}: {version(package)}")

print("python:", sys.version)
print("torch cuda available:", torch.cuda.is_available())
assert torch.cuda.is_available() is False

xb = np.random.random((10, 8)).astype("float32")
index = faiss.IndexFlatL2(8)
index.add(xb)
_, indices = index.search(xb[:1], 3)
assert indices.shape == (1, 3)

bm25 = BM25Okapi([["agent", "tool"], ["rag", "retrieval"]])
assert len(bm25.get_scores(["agent"])) == 2

engine = create_engine("sqlite+pysqlite:///:memory:")
with engine.begin() as conn:
    conn.execute(text("create table demo(id integer primary key, name text)"))
    conn.execute(text("insert into demo(name) values ('ok')"))
    assert conn.execute(text("select name from demo")).scalar() == "ok"

class State(TypedDict):
    x: int

def inc(state: State):
    return {"x": state["x"] + 1}

graph = StateGraph(State)
graph.add_node("inc", inc)
graph.add_edge(START, "inc")
graph.add_edge("inc", END)
app = graph.compile()
assert app.invoke({"x": 1})["x"] == 2

print("VERIFY_OK")
PY

echo "[DONE] $(date)"
