import os
import logging
from pathlib import Path
from typing import List, Dict, Any
import shutil

from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_community.document_loaders import TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document

from config.settings import VECTOR_DB_PATH, OPENAI_API_KEY, REPO_LOCAL_PATH

logger = logging.getLogger(__name__)

class CodeVectorDB:
    def __init__(self):
        self.vector_db_path = VECTOR_DB_PATH
        self.embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)
        self.vector_store = None
        
    def _get_code_files(self, project_path: Path) -> List[Path]:
        """Get all code files from project directory."""
        code_extensions = [
            '.py', '.java', '.js', '.ts', '.jsx', '.tsx', '.html', '.css', 
            '.c', '.cpp', '.h', '.hpp', '.cs', '.go', '.rs', '.rb', '.php',
            '.scala', '.kt', '.groovy', '.sh', '.bash', '.yml', '.yaml',
            '.json', '.xml', '.md', '.txt', '.gradle', '.pom', '.properties'
        ]
        
        code_files = []
        for ext in code_extensions:
            code_files.extend(list(project_path.glob(f"**/*{ext}")))
        
        # Filter out files in directories that should be ignored
        ignored_dirs = ['node_modules', 'venv', '.git', '.idea', '.vscode', 'target', 'build', 'dist']
        filtered_files = [
            f for f in code_files 
            if not any(ignored_dir in str(f) for ignored_dir in ignored_dirs)
        ]
        
        return filtered_files
    
    def _load_documents(self, file_paths: List[Path]) -> List[Document]:
        """Load documents from file paths."""
        documents = []
        
        for file_path in file_paths:
            try:
                # Only process text files
                if file_path.is_file():
                    try:
                        loader = TextLoader(str(file_path))
                        file_docs = loader.load()
                        
                        # Add file path as metadata
                        for doc in file_docs:
                            doc.metadata["source"] = str(file_path.relative_to(REPO_LOCAL_PATH))
                            doc.metadata["file_type"] = file_path.suffix
                        
                        documents.extend(file_docs)
                    except Exception as e:
                        logger.warning(f"Could not load {file_path}: {str(e)}")
            except Exception as e:
                logger.error(f"Error processing {file_path}: {str(e)}")
        
        return documents
    
    def embed_project(self, project_path: Path = REPO_LOCAL_PATH, force_refresh: bool = False):
        """Embed project code files into vector database."""
        if os.path.exists(self.vector_db_path) and not force_refresh:
            logger.info(f"Vector database already exists at {self.vector_db_path}. Loading...")
            self.vector_store = Chroma(persist_directory=self.vector_db_path, embedding_function=self.embeddings)
            return
            
        if os.path.exists(self.vector_db_path) and force_refresh:
            logger.info(f"Removing existing vector database at {self.vector_db_path}")
            shutil.rmtree(self.vector_db_path)
        
        logger.info(f"Embedding project code from {project_path}")
        
        # Get all code files
        code_files = self._get_code_files(project_path)
        logger.info(f"Found {len(code_files)} code files")
        
        # Load documents
        documents = self._load_documents(code_files)
        logger.info(f"Loaded {len(documents)} documents")
        
        # Split documents
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=2000,
            chunk_overlap=200,
            separators=["\n\n", "\n", " ", ""]
        )
        splits = text_splitter.split_documents(documents)
        logger.info(f"Split into {len(splits)} chunks")
        
        # Create and persist vector store
        self.vector_store = Chroma.from_documents(
            documents=splits,
            embedding=self.embeddings,
            persist_directory=self.vector_db_path
        )
        self.vector_store.persist()
        logger.info(f"Vector database created and persisted at {self.vector_db_path}")
    
    def query_codebase(self, query: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """Query the vector database for relevant code."""
        if not self.vector_store:
            self.embed_project()
        
        results = self.vector_store.similarity_search_with_score(query, k=n_results)
        
        formatted_results = []
        for doc, score in results:
            formatted_results.append({
                "content": doc.page_content,
                "source": doc.metadata.get("source", "Unknown"),
                "file_type": doc.metadata.get("file_type", "Unknown"),
                "relevance_score": score
            })
        
        return formatted_results
    
    def get_file_content(self, file_path: str) -> str:
        """Get the content of a specific file."""
        full_path = REPO_LOCAL_PATH / file_path
        if not full_path.exists():
            return f"File not found: {file_path}"
        
        try:
            return full_path.read_text(encoding='utf-8')
        except Exception as e:
            return f"Error reading file {file_path}: {str(e)}"
