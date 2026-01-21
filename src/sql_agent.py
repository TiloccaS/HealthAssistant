"""
SQL Agent per la gestione delle prenotazioni tramite chatbot.
Permette agli utenti di aggiungere, cancellare e visualizzare prenotazioni
interagendo direttamente con il database SQLite.
"""

import sqlite3
import requests
from datetime import datetime
from langchain_core.messages import SystemMessage
from langchain_core.tools import StructuredTool, ToolException
from langchain_ollama import ChatOllama
from langgraph.prebuilt import create_react_agent

from src.prompt import sql_agent_prompt
from config import DB_PATH, USER_NAME
from flask import session,request
# Backend API base URL
API_BASE_URL = "http://localhost:8000"


def get_all_available_slots() -> list[dict]:
    """
    Retrieve all available appointment slots.
    
    :return: List of available slots with id, doctor, and time.
    """
    db = sqlite3.connect(DB_PATH)
    cur = db.cursor()
    
    query = """
        SELECT a.id, a.doctor, a.time_slot, d.specialization
        FROM appointments a
        JOIN doctors d ON a.doctor = d.name
        WHERE a.patient IS NULL
        ORDER BY a.time_slot
    """
    
    result = cur.execute(query)
    slots = [
        {
            'slot_id': r[0],
            'doctor': r[1],
            'time_slot': r[2],
            'specialization': r[3]
        }
        for r in result.fetchall()
    ]
    db.close()
    return slots


def get_user_reservations(patient: str) -> list[dict]:
    """
    Retrieve all reservations for a patient.
    
    :param patient: Patient name.
    :return: List of patient's reservations.
    :raises ToolException: if user tries to access another patient's reservations.
    """
    
    
    db = sqlite3.connect(DB_PATH)
    cur = db.cursor()
    
    query = """
        SELECT a.id, a.doctor, a.time_slot, d.specialization
        FROM appointments a
        JOIN doctors d ON a.doctor = d.name
        WHERE LOWER(a.patient) = LOWER(?)
        ORDER BY a.time_slot
    """
    
    result = cur.execute(query, (patient,))
    reservations = [
        {
            'slot_id': r[0],
            'doctor': r[1],
            'time_slot': r[2],
            'specialization': r[3]
        }
        for r in result.fetchall()
    ]
    db.close()
    return reservations


def book_appointment(slot_id: int, patient: str) -> str:
    """
    Book an appointment for a patient via API.
    
    :param slot_id: ID of the slot to book.
    :param patient: Name of the patient booking.
    :return: Confirmation message or error.
    :raises ToolException: if user tries to book for others or slot is not available.
    """
    
    try:
        
        response = requests.post(
            f"{API_BASE_URL}/api/book-slot/{slot_id}",
            json={"patient": patient},
            timeout=10,          
            cookies=request.cookies  
        )
        
        if response.status_code == 200:
            data = response.json()
            # Get appointment details from DB for confirmation message
            db = sqlite3.connect(DB_PATH)
            cur = db.cursor()
            result = cur.execute(
                "SELECT doctor, time_slot FROM appointments WHERE id = ?", 
                (slot_id,)
            ).fetchone()
            db.close()
            
            if result:
                doctor, time_slot = result
                return f"✓ DATABASE UPDATED - BOOKING CONFIRMED: Appointment with {doctor} booked for {time_slot}. Slot ID: {slot_id}. The reservation has been saved to the database."
            return f"✓ DATABASE UPDATED - BOOKING CONFIRMED: Slot ID: {slot_id} has been booked."
        
        elif response.status_code == 404:
            raise ToolException(f"Slot with ID {slot_id} does not exist.")
        elif response.status_code == 400:
            raise ToolException(f"Slot with ID {slot_id} is already booked.")
        else:
            raise ToolException(f"Failed to book appointment: {response.json().get('error', 'Unknown error')}")
    
    except requests.exceptions.RequestException as e:
        raise ToolException(f"API request failed: {str(e)}")


def cancel_appointment(slot_id: int, patient: str) -> str:
    """
    Cancel an existing reservation via API.
    
    :param slot_id: ID of the slot to cancel.
    :param patient: Name of the patient canceling.
    :return: Confirmation message or error.
    :raises ToolException: if user tries to cancel another patient's reservation.
    """
    
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/cancel-slot/{slot_id}",
            json={"patient": patient},
            timeout=10,
            cookies=request.cookies 
        )
        print(response.status_code,response.json())
        if response.status_code == 200:
            data = response.json()
            message = data.get('message', f'Appointment cancelled successfully. Slot ID: {slot_id}')
            return f"✓ DATABASE UPDATED - CANCELLATION CONFIRMED: {message}. The slot is now available for other patients."
        
        elif response.status_code == 404:
            raise ToolException(f"Slot with ID {slot_id} does not exist.")
        elif response.status_code == 400:
            raise ToolException(f"Slot with ID {slot_id} has no reservation to cancel.")
        elif response.status_code == 403:
            raise ToolException(f"You cannot cancel this reservation. It belongs to another patient.")
        else:
            raise ToolException(f"Failed to cancel appointment: {response.json().get('error', 'Unknown error')}")
    
    except requests.exceptions.RequestException as e:
        raise ToolException(f"API request failed: {str(e)}")


def get_doctors_list() -> list[dict]:
    """
    Retrieve the list of all available doctors.
    
    :return: List of doctors with name and specialization.
    """
    db = sqlite3.connect(DB_PATH)
    cur = db.cursor()
    
    query = "SELECT name, specialization FROM doctors ORDER BY specialization"
    result = cur.execute(query)
    doctors = [
        {'name': r[0], 'specialization': r[1]}
        for r in result.fetchall()
    ]
    db.close()
    return doctors


def get_slots_by_doctor(doctor: str) -> list[dict]:
    """
    Retrieve available slots for a specific doctor.
    
    :param doctor: Name of the doctor.
    :return: Lista degli slot disponibili per quel dottore.
    """
    db = sqlite3.connect(DB_PATH)
    cur = db.cursor()
    
    query = """
        SELECT a.id, a.doctor, a.time_slot, d.specialization
        FROM appointments a
        JOIN doctors d ON a.doctor = d.name
        WHERE a.patient IS NULL AND LOWER(a.doctor) LIKE LOWER(?)
        ORDER BY a.time_slot
    """
    
    result = cur.execute(query, ('%' + doctor + '%',))
    slots = [
        {
            'slot_id': r[0],
            'doctor': r[1],
            'time_slot': r[2],
            'specialization': r[3]
        }
        for r in result.fetchall()
    ]
    db.close()
    return slots


def get_slots_by_specialization(specialization: str) -> list[dict]:
    """
    Retrieve available slots for a specific specialization.
    
    :param specialization: specialization to filter by.
    :return: List of available slots.
    """
    db = sqlite3.connect(DB_PATH)
    cur = db.cursor()
    
    query = """
        SELECT a.id, a.doctor, a.time_slot, d.specialization
        FROM appointments a
        JOIN doctors d ON a.doctor = d.name
        WHERE a.patient IS NULL AND LOWER(d.specialization) LIKE LOWER(?)
        ORDER BY a.time_slot
    """
    
    result = cur.execute(query, ('%' + specialization + '%',))
    slots = [
        {
            'slot_id': r[0],
            'doctor': r[1],
            'time_slot': r[2],
            'specialization': r[3]
        }
        for r in result.fetchall()
    ]
    db.close()
    return slots


def initialize_sql_agent(user_name: str, max_tokens: int = 512, temp: float = 0.1):
    """
    Inizializza l'agente SQL per la gestione delle prenotazioni.
    
    :param user_name: Nome dell'utente corrente.
    :param max_tokens: Numero massimo di token per la risposta.
    :param temp: Temperatura del modello LLM.
    :return: Agente LangChain configurato.
    """
    print("Initializing SQL Agent...")
    
    # Crea i tools
    tools = [
        StructuredTool.from_function(
            func=get_all_available_slots,
            name="get_all_available_slots",
            description="Recupera tutti gli slot disponibili per prenotazioni. Usa questo tool quando l'utente vuole vedere tutti gli appuntamenti disponibili.",
            handle_tool_error=True
        ),
        StructuredTool.from_function(
            func=get_user_reservations,
            name="get_user_reservations",
            description="Recupera tutte le prenotazioni dell'utente. Usa questo tool quando l'utente vuole vedere le proprie prenotazioni. Richiede il nome del paziente.",
            handle_tool_error=True
        ),
        StructuredTool.from_function(
            func=book_appointment,
            name="book_appointment",
            description="Prenota un appuntamento. Usa questo tool quando l'utente vuole prenotare uno slot. Richiede slot_id (numero intero) e patient (nome del paziente).",
            handle_tool_error=True
        ),
        StructuredTool.from_function(
            func=cancel_appointment,
            name="cancel_appointment",
            description="Cancella una prenotazione esistente. Usa questo tool quando l'utente vuole cancellare un appuntamento. Richiede slot_id (numero intero) e patient (nome del paziente).",
            handle_tool_error=True
        ),
        StructuredTool.from_function(
            func=get_doctors_list,
            name="get_doctors_list",
            description="Recupera la lista di tutti i dottori disponibili con le loro specializzazioni.",
            handle_tool_error=True
        ),
        StructuredTool.from_function(
            func=get_slots_by_doctor,
            name="get_slots_by_doctor",
            description="Recupera gli slot disponibili per un dottore specifico. Richiede il nome del dottore.",
            handle_tool_error=True
        ),
        StructuredTool.from_function(
            func=get_slots_by_specialization,
            name="get_slots_by_specialization",
            description="Recupera gli slot disponibili per una specializzazione specifica (es. Neurology, Cardiology).",
            handle_tool_error=True
        ),
    ]
    
    # Inizializza LLM
    llm = ChatOllama(model="llama3.1", temperature=temp, max_tokens=max_tokens)
    
    # Crea prompt di sistema
    prompt = SystemMessage(content=sql_agent_prompt.format(user_name=user_name))
    
    # Crea agente
    agent = create_react_agent(llm, tools, prompt=prompt)
    
    print("SQL Agent initialized!")
    return agent
