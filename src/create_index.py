import os
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import DirectoryLoader, UnstructuredXMLLoader, CSVLoader, TextLoader
import nltk

from helper import load_data, text_split, load_hf_embeddings
from config import *


# Data paths for different sources
MEDQUAD_PATH = os.path.join(ROOT_DIR, 'data', 'MedQuAD-master')
MIMIC_PATH = os.path.join(ROOT_DIR, 'data', 'MIMIC-III/mimiciii-demo/demo')


def fix_nltk():
	# If you get error from nltk package, add the required downloads here
	#nltk.download('all')
	nltk.download('punkt_tab')
	nltk.download('averaged_perceptron_tagger_eng')


def load_mimic_data(mimic_path):
	"""
	Load MIMIC-III data. Supports CSV and TXT files.
	MIMIC-III typically contains CSV files with clinical notes.
	
	:param mimic_path: Path to MIMIC-III data folder
	:return: List of loaded documents
	"""
	all_docs = []
	
	# Load CSV files (e.g., NOTEEVENTS.csv, DIAGNOSES_ICD.csv)
	if os.path.exists(mimic_path):
		# Try loading CSV files
		csv_pattern = "*.csv"
		try:
			csv_loader = DirectoryLoader(
				mimic_path, 
				glob=csv_pattern, 
				show_progress=True, 
				loader_cls=CSVLoader,
				loader_kwargs={"encoding": "utf-8"}
			)
			csv_docs = csv_loader.load()
			all_docs.extend(csv_docs)
			print(f"Loaded {len(csv_docs)} documents from MIMIC-III CSV files")
		except Exception as e:
			print(f"Warning: Could not load CSV files from MIMIC-III: {e}")
		
		# Try loading TXT files (clinical notes)
		txt_pattern = "**/*.txt"
		try:
			txt_loader = DirectoryLoader(
				mimic_path, 
				glob=txt_pattern, 
				show_progress=True, 
				loader_cls=TextLoader,
				loader_kwargs={"encoding": "utf-8"}
			)
			txt_docs = txt_loader.load()
			all_docs.extend(txt_docs)
			print(f"Loaded {len(txt_docs)} documents from MIMIC-III TXT files")
		except Exception as e:
			print(f"Warning: Could not load TXT files from MIMIC-III: {e}")
	else:
		print(f"Warning: MIMIC-III path not found: {mimic_path}")
		print("To use MIMIC-III, download the data and place it in data/MIMIC-III/")
	
	return all_docs


def create_combined_index(medquad_path, mimic_path, save_path, chunk_size, chunk_overlap):
	"""
	Create a combined FAISS index from MedQuAD and MIMIC-III data.
	
	:param medquad_path: Path to MedQuAD data
	:param mimic_path: Path to MIMIC-III data
	:param save_path: Path to save the FAISS index
	:param chunk_size: Size of text chunks
	:param chunk_overlap: Overlap between chunks
	:return: Combined vectorstore
	"""
	print("Creating combined index from MedQuAD + MIMIC-III...")
	fix_nltk()
	
	all_documents = []
	# Load MIMIC-III data
	print("\n=== Loading MIMIC-III data ===")
	mimic_data = load_mimic_data(mimic_path)
	all_documents.extend(mimic_data)
	
	# Load MedQuAD data
	print("\n=== Loading MedQuAD data ===")
	if os.path.exists(medquad_path):
		medquad_data = load_data(medquad_path)
		all_documents.extend(medquad_data)
		print(f"Loaded {len(medquad_data)} documents from MedQuAD")
	else:
		print(f"Warning: MedQuAD path not found: {medquad_path}")
	
	
	print(f"\n=== Total documents loaded: {len(all_documents)} ===")
	
	if not all_documents:
		raise ValueError("No documents loaded! Check your data paths.")
	
	# Split into chunks
	print("\nSplitting documents into chunks...")
	text_chunks = text_split(all_documents, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
	print(f"Created {len(text_chunks)} text chunks")
	
	# Load embeddings
	print("\nLoading embeddings...")
	embeddings = load_hf_embeddings()
	
	# Create vector store
	print("\nCreating vector store...")
	vectorstore = FAISS.from_documents(text_chunks, embedding=embeddings)
	vectorstore.save_local(save_path)
	
	print(f"\n=== Index saved to {save_path} ===")
	print("Done!")
	return vectorstore


def create_index(data_path, save_path, chunk_size, chunk_overlap):
	"""
	Original function for creating index from single data source (MedQuAD only).
	Kept for backward compatibility.
	"""
	print("Creating index...")
	fix_nltk()
	print("Loading data...")
	data = load_data(data_path)
	print("Data loaded...")
	text_chunks = text_split(data, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
	print("Loading embeddings...")
	embeddings = load_hf_embeddings()
	print("Creating vector store...")
	vectorstore_from_docs = FAISS.from_documents(text_chunks, embedding=embeddings)
	vectorstore_from_docs.save_local(save_path)
	print("Done!")
	return vectorstore_from_docs


if __name__ == '__main__':
	# Use combined index (MedQuAD + MIMIC-III)
	_ = create_combined_index(MEDQUAD_PATH, MIMIC_PATH, INDEX_PATH, CHUNK_SIZE, CHUNK_OVERLAP)