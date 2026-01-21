"""
Document Agent for analyzing laboratory reports (PDF).
Uses the medical knowledge base (FAISS) to provide advice on lab results.
"""

import os
import re
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_ollama import ChatOllama
from langchain_community.vectorstores import FAISS
from langchain_huggingface.embeddings import HuggingFaceEmbeddings

from src.prompt import lab_report_analysis_prompt
from config import INDEX_PATH, ASSETS_FOLDER

# Try to import PDF extraction libraries
try:
    import fitz  # PyMuPDF
    PDF_LIBRARY = "pymupdf"
except ImportError:
    try:
        from pypdf import PdfReader
        PDF_LIBRARY = "pypdf"
    except ImportError:
        PDF_LIBRARY = None
        print("WARNING: No PDF library found. Install pymupdf or pypdf for PDF analysis.")


def initialize_document_agent(max_tokens: int = 1024, temp: float = 0.1):
    """
    Initialize the Document Agent for analyzing laboratory reports.
    
    :param max_tokens: Maximum tokens for the response.
    :param temp: Temperature for the LLM.
    :return: Tuple of (LLM, retriever) for document analysis.
    """
    print("Initializing Document Agent...")
    
    # Load embeddings
    os.environ['HF_HOME'] = os.path.join(ASSETS_FOLDER, '.hf_cache')
    embeddings = HuggingFaceEmbeddings(model_name='sentence-transformers/all-MiniLM-L6-v2')
    
    # Load FAISS index for medical knowledge
    docsearch = FAISS.load_local(INDEX_PATH, embeddings, allow_dangerous_deserialization=True)
    retriever = docsearch.as_retriever(search_kwargs={"k": 3})
    
    # Load LLM
    llm = ChatOllama(model="llama3.1", temperature=temp, max_tokens=max_tokens)
    
    print("Document Agent initialized!")
    return llm, retriever


def extract_text_from_pdf(file_path: str) -> str:
    """
    Extract text content from a PDF file.
    
    :param file_path: Path to the PDF file.
    :return: Extracted text content.
    """
    if not os.path.exists(file_path):
        return ""
    
    if PDF_LIBRARY == "pymupdf":
        return _extract_with_pymupdf(file_path)
    elif PDF_LIBRARY == "pypdf":
        return _extract_with_pypdf(file_path)
    else:
        return "ERROR: No PDF library available. Please install pymupdf or pypdf."


def _extract_with_pymupdf(file_path: str) -> str:
    """Extract text using PyMuPDF (fitz)."""
    try:
        doc = fitz.open(file_path)
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        return text
    except Exception as e:
        return f"Error extracting PDF: {str(e)}"


def _extract_with_pypdf(file_path: str) -> str:
    """Extract text using pypdf."""
    try:
        from pypdf import PdfReader
        reader = PdfReader(file_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        return text
    except Exception as e:
        return f"Error extracting PDF: {str(e)}"



def search_medical_info(retriever, query: str) -> str:
    """
    Search medical information using the FAISS retriever.
    
    :param retriever: The FAISS retriever.
    :param query: Search query.
    :return: Retrieved medical information.
    """
    docs = retriever.invoke(query)
    if docs:
        return "\n\n".join([doc.page_content for doc in docs])
    return "No relevant medical information found."


def analyze_lab_report(llm, retriever, file_path: str) -> str:
    """
    Analyze a laboratory report PDF and provide advice using medical knowledge base.
    
    :param llm: The LLM instance.
    :param retriever: The FAISS retriever for medical information.
    :param file_path: Path to the PDF file.
    :return: Structured analysis with advice.
    """
    # Extract text from PDF
    pdf_text = extract_text_from_pdf(file_path)
    
    if not pdf_text.strip():
        return "Could not extract text from the PDF. The file may be empty, corrupted, or image-based (scanned document)."
    
    if pdf_text.startswith("ERROR:"):
        return f"{pdf_text}"
    
    # Single FAISS search for general lab report information (much faster)
    query = "laboratory blood test results analysis interpretation abnormal values medical advice"
    medical_context = search_medical_info(retriever, query)
    
    # Create the prompt - let LLM handle all the interpretation
    system_message = SystemMessage(content=lab_report_analysis_prompt)
    user_message = HumanMessage(
        content=f"""Please analyze this laboratory report and provide helpful advice.

LABORATORY REPORT TEXT:
{pdf_text}

MEDICAL KNOWLEDGE BASE INFORMATION:
{medical_context if medical_context and "No relevant" not in medical_context else "General medical knowledge available for interpretation."}

Please provide a clear analysis identifying any abnormal values and giving advice for the patient."""
    )
    
    try:
        response = llm.invoke([system_message, user_message])
        return response.content
    except Exception as e:
        return f"Error analyzing document: {str(e)}"
