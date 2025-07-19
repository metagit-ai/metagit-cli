#! /usr/bin/env python3
"""
Index tools for the detect flow
"""

import os
from pathlib import Path

from crewai import ToolResponse, tool
from langchain.embeddings import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.vectorstores import FAISS


@tool
def index_repo(
    repo_path: str, chunk_size: int = 1000, chunk_overlap: int = 200
) -> ToolResponse:
    """
    Walk the repo, split files, embed, and store in FAISS.
    Returns index metadata location.
    """
    try:
        embeddings = OpenAIEmbeddings()
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size, chunk_overlap=chunk_overlap
        )
        docs = []
        for root, _, files in os.walk(repo_path):
            for fn in files:
                if fn.endswith((".py", ".json", ".yaml", ".yml")):
                    full = Path(root) / fn
                    text = full.read_text(encoding="utf-8")
                    for i, chunk in enumerate(text_splitter.split_text(text)):
                        docs.append(
                            {
                                "page_content": chunk,
                                "metadata": {"path": str(full), "chunk": i},
                            }
                        )
        vectorstore = FAISS.from_documents(
            [d["page_content"] for d in docs],
            embeddings,
            metadatas=[d["metadata"] for d in docs],
        )
        vectorstore.save_local(f"{repo_path}/.repo_index")
        return ToolResponse(
            success=True, data={"index_path": f"{repo_path}/.repo_index"}
        )
    except Exception as e:
        return ToolResponse(success=False, error=str(e))
