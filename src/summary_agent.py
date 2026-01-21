"""
Summary Agent for extracting structured consultation summaries from chat history.
"""

import os
import sqlite3
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_ollama import ChatOllama

from src.prompt import summary_agent_prompt, patient_problem_prompt
from config import CHAT_HISTORY_FOLDER, DB_PATH


def get_user_appointments(user_name: str) -> str:
    """
    Get the user's booked appointments from the database.
    
    :param user_name: The user's name.
    :return: Formatted string with appointments or "None" if no appointments.
    """
    try:
        db = sqlite3.connect(DB_PATH)
        cur = db.cursor()
        
        query = """
            SELECT a.time_slot, a.doctor, d.specialization
            FROM appointments a
            JOIN doctors d ON a.doctor = d.name
            WHERE LOWER(a.patient) LIKE LOWER(?)
            ORDER BY a.time_slot
        """
        
        result = cur.execute(query, ('%' + user_name + '%',))
        rows = result.fetchall()
        db.close()
        
        if not rows:
            return "None"
        
        appointments = []
        for row in rows:
            time_slot, doctor, specialization = row
            appointments.append(f"{doctor} ({specialization}) - {time_slot}")
        
        return "; ".join(appointments)
    except Exception as e:
        print(f"Error fetching appointments: {e}")
        return "Unable to retrieve"


def initialize_summary_agent(max_tokens: int = 512, temp: float = 0.1):
    """
    Initialize the Summary Agent for consultation summaries.
    
    :param max_tokens: Maximum tokens for the response.
    :param temp: Temperature for the LLM.
    :return: Configured LLM for summaries.
    """
    print("Initializing Summary Agent...")
    
    llm = ChatOllama(model="llama3.1", temperature=temp, max_tokens=max_tokens)
    
    print("Summary Agent initialized!")
    return llm


def read_chat_history_from_file(user_name: str) -> str:
    """
    Read chat history from the user's chat history file.
    
    :param user_name: The user's name (will be lowercased for filename).
    :return: The content of the chat history file.
    """
    filename = f"{user_name.lower()}.txt"
    filepath = os.path.join(CHAT_HISTORY_FOLDER, filename)
    
    if not os.path.exists(filepath):
        return ""
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"Error reading chat history file: {e}")
        return ""


def generate_consultation_summary(llm, user_name: str) -> str:
    """
    Generate a structured consultation summary from chat history file.
    
    :param llm: The LLM instance.
    :param user_name: The user's name to find their chat history file.
    :return: Formatted consultation summary.
    """
    # Read conversation from file
    conversation_text = read_chat_history_from_file(user_name)
    
    if not conversation_text.strip():
        return "No consultation history available to summarize."
    
    # Get user's current appointments from database
    appointments = get_user_appointments(user_name)
    
    # Create the prompt with chat history and appointments info
    system_message = SystemMessage(content=summary_agent_prompt)
    user_message = HumanMessage(
        content=f"""Please analyze the following conversation and provide a structured consultation summary.

CURRENT USER APPOINTMENTS (from database): {appointments}

CONVERSATION HISTORY:
{conversation_text}"""
    )
    
    try:
        response = llm.invoke([system_message, user_message])
        return response.content
    except Exception as e:
        return f"Error generating summary: {str(e)}"


def generate_patient_problem_summary(llm, user_name: str) -> str:
    """
    Generate a brief patient problem summary from chat history for appointment booking.
    
    :param llm: The LLM instance.
    :param user_name: The user's name to find their chat history file.
    :return: Brief problem summary (1-2 sentences).
    """
    # Read conversation from file
    conversation_text = read_chat_history_from_file(user_name)
    
    if not conversation_text.strip():
        return "General consultation"
    
    # Create the prompt with chat history
    system_message = SystemMessage(content=patient_problem_prompt)
    user_message = HumanMessage(content=conversation_text)
    
    try:
        response = llm.invoke([system_message, user_message])
        # Ensure the response is not too long (max 200 chars)
        problem = response.content.strip()
        if len(problem) > 200:
            problem = problem[:197] + "..."
        return problem if problem else "General consultation"
    except Exception as e:
        print(f"Error generating patient problem summary: {e}")
        return "General consultation"
