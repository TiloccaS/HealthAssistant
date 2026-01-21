import os
import datetime
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import DirectoryLoader, UnstructuredXMLLoader, CSVLoader
from langchain_huggingface.embeddings import HuggingFaceEmbeddings
from langchain_ollama import ChatOllama
from langchain_community.vectorstores import FAISS
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain_core.tools.retriever import create_retriever_tool
from langgraph.prebuilt import create_react_agent
from langchain_core.tools import StructuredTool, ToolException
import sqlite3
import sys
import os

try:
    from src.prompt import prompt_template
except ModuleNotFoundError:
    from prompt import prompt_template

from config import *


def load_data(data_path):
    loader = DirectoryLoader(data_path, glob="*/*.xml", show_progress=True, loader_cls=UnstructuredXMLLoader)
    data = loader.load()
    return data

def text_split(data, chunk_size=500, chunk_overlap=20):
    splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    text_chunks = splitter.split_documents(data)
    return text_chunks

def load_hf_embeddings():
    os.environ['HF_HOME'] = os.path.join(ASSETS_FOLDER, '.hf_cache')
    return HuggingFaceEmbeddings(model_name='sentence-transformers/all-MiniLM-L6-v2')

def parse_results(result):
    return result['messages'], result['messages'][-1].content


def initialize_llm(user_name, host, k=2, max_tokens=512, temp=0.1):
    # Load embeddings
    print("Loading embeddings...")
    embeddings = load_hf_embeddings()#it says how make embeddings from text using huggingface model
    
    # Load index
    print("Loading index...")
    docsearch = FAISS.load_local(INDEX_PATH, embeddings, allow_dangerous_deserialization=True)
    retriever = docsearch.as_retriever(search_kwargs={"k": k})
    retriever_tool = create_retriever_tool(
        retriever, 
        name="search_medical_information", 
        description="MANDATORY: You MUST use this tool FIRST whenever the user mentions symptoms, health problems, medical conditions, or asks health-related questions. This retrieves accurate medical information from our knowledge base. ALWAYS call this before giving any medical advice. Never answer health questions without using this tool first."
    )
    tools = [retriever_tool]
    
    # Load LLM
    print("Loading LLM...")
    llm = ChatOllama(model="llama3.1", temperature=temp, max_tokens=max_tokens)
    
    # Load DB
    db = SQLDatabase.from_uri("sqlite:///" + DB_PATH)
    toolkit = SQLDatabaseToolkit(db=db, llm=llm)
    #tools += toolkit.get_tools()
    
    # Create additional tools
    search_available_doctor_appointments_tool = StructuredTool.from_function(func=search_available_doctor_appointments, name="search_available_doctor_appointments", description="Use to look up available time slots for appointments with a specific doctor. Returns slots with doctor name, specialization, and slot ID.", handle_tool_error=True)
    get_all_available_slots_tool = StructuredTool.from_function(func=get_all_available_slots_for_booking, name="get_all_available_slots", description="Use when the user wants to see ALL available appointment slots or wants to book but hasn't specified a doctor. Returns all available slots grouped by doctor with specialization.", handle_tool_error=True)
    search_patient_appointments_tool = StructuredTool.from_function(func=search_patient_appointments, name="search_patient_appointments", description="Use to look up the list of appointments currently scheduled by the patient", handle_tool_error=True)
    tools += [retriever_tool, search_available_doctor_appointments_tool, get_all_available_slots_tool, search_patient_appointments_tool]
    
    # Create agent
    print("Loading agent...")
    prompt = SystemMessage(content=prompt_template.format(user_name=user_name, table_names=db.get_usable_table_names(), host=host))
    agent = create_react_agent(
        llm,
        tools,
        prompt=prompt
    )

    
    print("Done!")
    
    return agent


def search_available_doctor_appointments(doctor: str) -> str:
    """
    Look up available time slots for appointments with a given doctor.

    :param doctor: The name of the doctor.
    :return: A formatted string with available time slots grouped by doctor with specialization.
    """
    
    # Open connection to DB
    db = sqlite3.connect(DB_PATH)
    cur = db.cursor()
    
    # Prepare query to retrieve time slot information with JOIN for specialization
    query = """
                SELECT a.id, a.time_slot, a.doctor, d.specialization
                FROM appointments a
                JOIN doctors d ON a.doctor = d.name
                WHERE a.patient IS NULL AND LOWER(a.doctor) LIKE LOWER(?)
                ORDER BY a.doctor, a.time_slot
            """
    
    # Execute query and fetch result
    result = cur.execute(query, ('%' + doctor + '%',))
    rows = result.fetchall()
    db.close()
    
    if not rows:
        return f"No available slots found for doctor '{doctor}'."
    
    # Format output
    slots_list = [f"- Slot ID {r[0]}: {r[2]} ({r[3]}) - {r[1]}" for r in rows]
    return "AVAILABLE SLOTS:\n" + "\n".join(slots_list) + "\n\nTo book an appointment, the user needs to use the appointment management system with the slot ID."


def get_all_available_slots_for_booking() -> str:
    """
    Get all available appointment slots grouped by doctor with their specialization.
    Use this when the user wants to book an appointment but hasn't specified a doctor.
    
    :return: A formatted string with all available slots grouped by doctor.
    """
    db = sqlite3.connect(DB_PATH)
    cur = db.cursor()
    
    query = """
        SELECT a.id, a.doctor, a.time_slot, d.specialization
        FROM appointments a
        JOIN doctors d ON a.doctor = d.name
        WHERE a.patient IS NULL
        ORDER BY d.specialization, a.doctor, a.time_slot
    """
    
    result = cur.execute(query)
    rows = result.fetchall()
    db.close()
    
    if not rows:
        return "No available appointment slots at the moment."
    
    # Group by doctor
    from collections import defaultdict
    grouped = defaultdict(list)
    for r in rows:
        slot_id, doctor, time_slot, specialization = r
        grouped[(doctor, specialization)].append((slot_id, time_slot))
    
    # Format output
    output_lines = ["ALL AVAILABLE APPOINTMENT SLOTS (grouped by doctor):"]
    for (doctor, specialization), slots in grouped.items():
        output_lines.append(f"\n**{doctor}** ({specialization}):")
        for slot_id, time_slot in slots:
            output_lines.append(f"  - Slot ID {slot_id}: {time_slot}")
    
    output_lines.append("\nTo book, the user should use the appointment management system with the desired slot ID.")
    return "\n".join(output_lines)

def search_patient_appointments(patient: str, doctor: str = None) -> list[dict]:
    """
    Look up scheduled appointments of a patient with a given doctor.

    :param patient: The name of the patient.
    :param doctor: The name of the doctor. If null returns the patient appointments with all doctors.
    :return: A list of time slots of scheduled appointments with the corresponding doctor and reservation link.
    :raises ToolException: if the user is trying to access information of another patient.
    """
    
    
    # Open connection to DB
    db = sqlite3.connect(DB_PATH)
    cur = db.cursor()
    
    if doctor is not None and doctor != '':
        # Prepare query to retrieve time slot information
        query = """
                    SELECT id, time_slot, doctor
                    FROM appointments
                    WHERE LOWER(patient) LIKE LOWER(?) and LOWER(doctor) LIKE LOWER(?)
                """
    
        # Execute query and fetch result
        result = cur.execute(query, ('%' + patient + '%', '%' + doctor + '%',))
    else:
        # Prepare query to retrieve time slot information
        query = """
                    SELECT id, time_slot, doctor
                    FROM appointments
                    WHERE LOWER(patient) LIKE LOWER(?)
                """
        # Execute query and fetch result
        result = cur.execute(query, ('%' + patient + '%',))
    
    return list(({'time_slot': r[1],'doctor': r[2],  'reservation_link': '<a href="res?id={}" target="_blank"> link </a>'.format(r[0])} for r in result.fetchall()))
