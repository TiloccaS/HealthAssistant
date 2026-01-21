from src.document_agent import search_medical_info
import sys
import os
import sqlite3
import secrets
from typing import Dict, List
from datetime import datetime
from werkzeug.utils import secure_filename

from flask import Flask, jsonify, request, send_file, render_template, g, make_response
from flask_cors import CORS
from flask_sock import Sock
from dotenv import load_dotenv

from src import initialize_llm, parse_results, initialize_sql_agent, initialize_summary_agent, generate_consultation_summary, generate_patient_problem_summary, initialize_document_agent, analyze_lab_report
# Authentication module - uses Flask session cookies to remember logged-in users
from src.auth import (
    register_user, login_user, logout_user,
    get_current_user, login_required, doctor_required, admin_required,
    get_doctor_for_user
)
from config import *

# --- Load env ---
load_dotenv()


def get_current_user_name():
    """
    Get the current authenticated user's full name.
    Falls back to USER_NAME from config if not authenticated.
    """
    user = get_current_user()
    if user:
        return user['full_name']
    return USER_NAME  # Fallback for backwards compatibility

# --- Upload configuration ---
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'assets', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'doc', 'docx'}
MAX_FILE_SIZE = 2 * 1024 * 1024  # 2MB in bytes
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_chat_message(role: str, message: str, user_name: str = None):
    """
    Save a chat message to the user's chat history file.
    
    :param role: 'user' or 'bot'
    :param message: The message text
    :param user_name: The user's name (optional, defaults to global USER_NAME)
    """
    if user_name is None:
        user_name = USER_NAME
    os.makedirs(CHAT_HISTORY_FOLDER, exist_ok=True)
    print("the username for chat history is",user_name)
    filepath = os.path.join(CHAT_HISTORY_FOLDER, f"{user_name.lower()}.txt")
    timestamp = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
    
    with open(filepath, 'a', encoding='utf-8') as f:
        f.write(f"[{timestamp}] {role}: {message}\n\n")

def ensure_user_chat_history_exists(user_name: str = None):
    """
    Ensure the chat history file exists for the specified user.
    Creates an empty file if it doesn't exist.
    """
    if user_name is None:
        user_name = USER_NAME
    os.makedirs(CHAT_HISTORY_FOLDER, exist_ok=True)
    filepath = os.path.join(CHAT_HISTORY_FOLDER, f"{user_name.lower()}.txt")
    if not os.path.exists(filepath):
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("")  # Create empty file
        print(f"Created new chat history file for user: {user_name}")

# Create chat history file for current user if it doesn't exist
ensure_user_chat_history_exists()

# --- Initialize LLM / Agent ---
"""try:
    agent = initialize_llm(USER_NAME, HOST, k=K, max_tokens=MAX_TOKENS, temp=T)
    print("LLM agent initialized")
except Exception as e:
    print("LLM init error:", e)
    sys.exit(1)
"""
# --- Initialize SQL Agent ---
"""try:
    sql_agent = initialize_sql_agent(USER_NAME, max_tokens=MAX_TOKENS, temp=T)
    print("SQL agent initialized")
except Exception as e:
    print("SQL agent init error:", e)
    sys.exit(1)
"""
# --- Initialize Summary Agent ---
try:
    summary_llm = initialize_summary_agent(max_tokens=MAX_TOKENS, temp=T)
    print("Summary agent initialized")
except Exception as e:
    print("Summary agent init error:", e)
    sys.exit(1)

# --- Initialize Document Agent ---
try:
    document_llm, doc_retriever = initialize_document_agent(max_tokens=MAX_TOKENS, temp=T)
    print("Document agent initialized")
except Exception as e:
    print("Document agent init error:", e)
    document_llm, doc_retriever = None, None
    print("Document agent NOT available - PDF analysis will be disabled")

# =============================================================================
# FLASK APP SETUP
# =============================================================================

app = Flask(__name__)

# Allow frontend to make requests to backend (CORS = Cross-Origin Resource Sharing)
CORS(app, 
     origins=["http://localhost:5173", "http://localhost:5174", "http://localhost:5175"], 
     supports_credentials=True)  # Allow cookies to be sent

# Add WebSocket support
sock = Sock(app)

# Secret key for signing session cookies
# In production, set SECRET_KEY environment variable to a fixed value
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(32))

# Configure Flask sessions
from datetime import timedelta
app.config['SESSION_COOKIE_HTTPONLY'] = True   # Cookie not accessible via JavaScript
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # CSRF protection
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)  # Session expires after 24h

# Store active WebSocket connections
active_connections: Dict[int, List[dict]] = {}


# =============================================================================
# AUTHENTICATION ENDPOINTS
# =============================================================================

@app.post("/api/auth/register")
def api_register():
    """
    Create a new user account.
    
    Expected JSON body:
    {
        "username": "john",
        "email": "john@example.com",
        "password": "SecurePass123!",
        "full_name": "John Doe"
    }
    """
    print("POST /api/auth/register called")
    
    # Get JSON data from request body
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    # Extract fields
    username = data.get('username', '').strip()
    email = data.get('email', '').strip()
    password = data.get('password', '')
    full_name = data.get('full_name', '').strip()
    
# Try to register (always as patient - doctors/admins are created manually in DB)
    success, result = register_user(username, email, password, full_name, 'patient')
    
    if not success:
        return jsonify({"error": result}), 400
    
    return jsonify({
        "success": True,
        "message": "Registration successful",
        "user_id": result
    }), 201


@app.post("/api/auth/login")
def api_login():
    """
    Log in with username/email and password.
    Creates a session cookie on success.
    
    Expected JSON body:
    {
        "username": "john",  (or email)
        "password": "SecurePass123!"
    }
    """
    print("POST /api/auth/login called")
    
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    username_or_email = data.get('username', '').strip()
    password = data.get('password', '')
    
    if not username_or_email or not password:
        return jsonify({"error": "Username and password are required"}), 400
    
    # Try to authenticate (this also creates the Flask session)
    success, error, user_info = login_user(username_or_email, password)
    
    if not success:
        return jsonify({"error": error}), 401
    
    # Return success response (session cookie is set automatically by Flask)
    return jsonify({
        "success": True,
        "message": "Login successful",
        "user": user_info
    })


@app.post("/api/auth/logout")
def api_logout():
    """
    Log out the current user by clearing the session.
    """
    print("POST /api/auth/logout called")
    
    # Clear Flask session
    logout_user()#session.clear()
    
    return jsonify({
        "success": True,
        "message": "Logged out successfully"
    })


@app.get("/api/auth/me")
def api_get_current_user():
    """
    Get the current authenticated user.
    """
    print("GET /api/auth/me called")
    
    user = get_current_user()
    
    if not user:
        return jsonify({"authenticated": False}), 401
    
    # If user is a doctor, get their doctor info
    doctor_info = None
    if user['role'] == 'doctor':
        doctor_info = get_doctor_for_user(user['user_id'])
    
    return jsonify({
        "authenticated": True,
        "user": user,
        "doctor_info": doctor_info
    })


# ======================================================
# Doctor-Specific Endpoints
# ======================================================
@app.get("/api/doctor/patients")
@login_required
@doctor_required
def api_doctor_patients():
    """
    Get all patients who have appointments with the current doctor.
    """
    print("GET /api/doctor/patients called")
    
    user = g.current_user
    doctor_info = get_doctor_for_user(user['user_id'])
    
    if not doctor_info:
        return jsonify({"error": "Doctor profile not found"}), 404
    
    doctor_name = doctor_info['name']
    
    db = sqlite3.connect(DB_PATH)
    cur = db.cursor()
    
    # Get all unique patients with their appointments
    query = """
        SELECT DISTINCT a.patient, a.id, a.time_slot, a.patient_problem
        FROM appointments a
        WHERE a.doctor = ? AND a.patient IS NOT NULL
        ORDER BY a.time_slot DESC
    """
    
    result = cur.execute(query, (doctor_name,))
    rows = result.fetchall()
    db.close()
    
    # Group appointments by patient
    patients_dict = {}
    for row in rows:
        patient_name, slot_id, time_slot, problem = row
        if patient_name not in patients_dict:
            patients_dict[patient_name] = {
                'name': patient_name,
                'appointments': []
            }
        patients_dict[patient_name]['appointments'].append({
            'slot_id': slot_id,
            'time_slot': time_slot,
            'problem': problem
        })
    
    patients = list(patients_dict.values())
    
    return jsonify({
        'doctor': doctor_info,
        'patients': patients,
        'total_patients': len(patients)
    })


@app.get("/api/doctor/appointments")
@login_required
@doctor_required
def api_doctor_appointments():
    """
    Get all appointments for the current doctor.
    """
    print("GET /api/doctor/appointments called")
    
    user = g.current_user
    doctor_info = get_doctor_for_user(user['user_id'])
    
    if not doctor_info:
        return jsonify({"error": "Doctor profile not found"}), 404
    
    doctor_name = doctor_info['name']
    
    db = sqlite3.connect(DB_PATH)
    cur = db.cursor()
    
    # Get all appointments (both booked and available)
    query = """
        SELECT a.id, a.time_slot, a.patient, a.patient_problem
        FROM appointments a
        WHERE a.doctor = ?
        ORDER BY a.time_slot
    """
    
    result = cur.execute(query, (doctor_name,))
    appointments = [
        {
            'slot_id': r[0],
            'time_slot': r[1],
            'patient': r[2],
            'patient_problem': r[3],
            'status': 'booked' if r[2] else 'available'
        }
        for r in result.fetchall()
    ]
    db.close()
    
    # Separate into booked and available
    booked = [a for a in appointments if a['status'] == 'booked']
    available = [a for a in appointments if a['status'] == 'available']
    
    return jsonify({
        'doctor': doctor_info,
        'appointments': {
            'booked': booked,
            'available': available,
            'total_booked': len(booked),
            'total_available': len(available)
        }
    })


@app.get("/api/doctor/patient/<patient_name>")
@login_required
@doctor_required
def api_doctor_patient_detail(patient_name):
    """
    Get detailed information about a specific patient including chat history.
    """
    print(f"GET /api/doctor/patient/{patient_name} called")
    
    user = g.current_user
    print("user is:",user)
    doctor_info = get_doctor_for_user(user['user_id'])
    
    if not doctor_info:
        return jsonify({"error": "Doctor profile not found"}), 404
    
    doctor_name = doctor_info['name']
    
    db = sqlite3.connect(DB_PATH)
    cur = db.cursor()
    
    # Verify this patient has an appointment with this doctor
    verify_query = """
        SELECT COUNT(*) FROM appointments
        WHERE doctor = ? AND LOWER(patient) = LOWER(?)
    """
    result = cur.execute(verify_query, (doctor_name, patient_name)).fetchone()
    
    if result[0] == 0:
        db.close()
        return jsonify({"error": "Patient not found or not assigned to you"}), 404
    
    # Get patient's appointments with this doctor
    appointments_query = """
        SELECT a.id, a.time_slot, a.patient_problem
        FROM appointments a
        WHERE a.doctor = ? AND LOWER(a.patient) = LOWER(?)
        ORDER BY a.time_slot
    """
    
    result = cur.execute(appointments_query, (doctor_name, patient_name))
    appointments = [
        {
            'slot_id': r[0],
            'time_slot': r[1],
            'problem': r[2]
        }
        for r in result.fetchall()
    ]
    
    # Get patient's documents (if any)
    docs_query = """
        SELECT id, document_path, upload_date, description
        FROM documents
        WHERE LOWER(patient_surname) = LOWER(?)
        ORDER BY upload_date DESC
    """
    result = cur.execute(docs_query, (patient_name,))
    documents = [
        {
            'id': r[0],
            'filename': os.path.basename(r[1]),
            'upload_date': r[2],
            'description': r[3]
        }
        for r in result.fetchall()
    ]
    db.close()
    
    # Get patient's chat history
    chat_history = []
    chat_path = os.path.join(CHAT_HISTORY_FOLDER, f"{patient_name.lower()}.txt")
    if os.path.exists(chat_path):
        import re
        with open(chat_path, 'r', encoding='utf-8') as f:
            content = f.read()
            pattern = r'\[(\d{2}-\d{2}-\d{4} \d{2}:\d{2}:\d{2})\] (user|bot): (.+?)(?=\n\[|\Z)'
            matches = re.findall(pattern, content, re.DOTALL)
            
            for match in matches:
                timestamp, role, text = match
                chat_history.append({
                    'timestamp': timestamp,
                    'role': role,
                    'text': text.strip()
                })
    
    return jsonify({
        'patient': {
            'name': patient_name.title(),
            'appointments': appointments,
            'documents': documents
        },
        'chat_history': chat_history,
        'doctor': doctor_info
    })


@app.post("/api/doctor/generate-problem/<int:appointment_id>")
@login_required
@doctor_required
def api_doctor_generate_problem(appointment_id):
    """
    Generate patient problem summary from chat history for a specific appointment.
    Only the doctor assigned to this appointment can generate the summary.
    """
    print(f"POST /api/doctor/generate-problem/{appointment_id} called")
    
    user = g.current_user
    doctor_info = get_doctor_for_user(user['user_id'])
    
    if not doctor_info:
        return jsonify({"error": "Doctor profile not found"}), 404
    
    doctor_name = doctor_info['name']
    
    db = sqlite3.connect(DB_PATH)
    cur = db.cursor()
    
    # Verify this appointment belongs to this doctor and get patient name
    verify_query = """
        SELECT id, patient, doctor FROM appointments
        WHERE id = ?
    """
    result = cur.execute(verify_query, (appointment_id,)).fetchone()
    
    if not result:
        db.close()
        return jsonify({"error": "Appointment not found"}), 404
    
    if result[2] != doctor_name:
        db.close()
        return jsonify({"error": "You can only generate summaries for your own patients"}), 403
    
    patient_name = result[1]
    
    if not patient_name:
        db.close()
        return jsonify({"error": "This appointment has no patient assigned"}), 400
    
    # Generate the patient problem summary
    try:
        patient_problem = generate_patient_problem_summary(summary_llm, patient_name)
        print(f"Generated patient problem for {patient_name}: {patient_problem}")
        
        # Update the appointment with the generated problem
        update_query = "UPDATE appointments SET patient_problem = ? WHERE id = ?"
        cur.execute(update_query, (patient_problem, appointment_id))
        db.commit()
        db.close()
        
        return jsonify({
            "success": True,
            "patient_problem": patient_problem,
            "message": "Problem summary generated successfully"
        })
    except Exception as e:
        db.close()
        print(f"Error generating patient problem: {e}")
        return jsonify({"error": f"Failed to generate summary: {str(e)}"}), 500


@app.get("/api/doctor/dashboard")
@login_required
@doctor_required
def api_doctor_dashboard():
    """
    Get dashboard data for the doctor.
    """
    print("GET /api/doctor/dashboard called")
    
    user = g.current_user
    doctor_info = get_doctor_for_user(user['user_id'])
    
    if not doctor_info:
        return jsonify({"error": "Doctor profile not found"}), 404
    
    doctor_name = doctor_info['name']
    
    db = sqlite3.connect(DB_PATH)
    cur = db.cursor()
    
    # Count total patients
    patients_query = """
        SELECT COUNT(DISTINCT patient) FROM appointments
        WHERE doctor = ? AND patient IS NOT NULL
    """
    total_patients = cur.execute(patients_query, (doctor_name,)).fetchone()[0]
    
    # Count upcoming appointments (booked)
    booked_query = """
        SELECT COUNT(*) FROM appointments
        WHERE doctor = ? AND patient IS NOT NULL
    """
    total_booked = cur.execute(booked_query, (doctor_name,)).fetchone()[0]
    
    # Count available slots
    available_query = """
        SELECT COUNT(*) FROM appointments
        WHERE doctor = ? AND patient IS NULL
    """
    total_available = cur.execute(available_query, (doctor_name,)).fetchone()[0]
    
    # Get next 5 upcoming appointments
    upcoming_query = """
        SELECT a.id, a.time_slot, a.patient, a.patient_problem
        FROM appointments a
        WHERE a.doctor = ? AND a.patient IS NOT NULL
        ORDER BY a.time_slot
        LIMIT 5
    """
    result = cur.execute(upcoming_query, (doctor_name,))
    upcoming = [
        {
            'slot_id': r[0],
            'time_slot': r[1],
            'patient': r[2],
            'problem': r[3]
        }
        for r in result.fetchall()
    ]
    
    db.close()
    
    return jsonify({
        'doctor': doctor_info,
        'stats': {
            'total_patients': total_patients,
            'total_booked': total_booked,
            'total_available': total_available
        },
        'upcoming_appointments': upcoming
    })

# --- Router keywords for SQL Agent ---
SQL_AGENT_KEYWORDS = [
    # Booking
    "book", "booking", "reserve", "reservation", "reservations",
    # Cancellation
    "cancel", "cancellation", "delete", "remove",
    # Viewing slots/appointments
    "slot", "slots", "available", "availability",
    "my appointments", "my bookings", "my reservations",
    # Appointments
    "appointment", "appointments",
    # Database
    "database", "db",
    # Specific actions
    "slot_id", "slot id",
]

# --- Router keywords for Summary Agent ---
SUMMARY_AGENT_KEYWORDS = [
    "summary", "summarize", "summarise", "recap", "recapitulate",
    "consultation summary", "consultation report",
    "what did we discuss", "what we discussed",
    "give me a summary", "show summary",
]

def should_use_sql_agent(message: str) -> bool:
    """
    Determines if the user message requires the SQL Agent.
    """
    msg_lower = message.lower()
    return any(keyword in msg_lower for keyword in SQL_AGENT_KEYWORDS)

def get_all_doctors_list() -> str:
    """
    Retrieves all doctors with their specializations from the database.
    Returns a formatted string to include in the agent context.
    """
    db = sqlite3.connect(DB_PATH)
    cur = db.cursor()
    
    query = "SELECT name, specialization FROM doctors ORDER BY specialization, name"
    result = cur.execute(query)
    rows = result.fetchall()
    db.close()
    
    if not rows:
        return "NO DOCTORS AVAILABLE in the system."
    
    # Group by specialization
    from collections import defaultdict
    by_spec = defaultdict(list)
    for name, spec in rows:
        by_spec[spec].append(name)
    
    lines = ["AVAILABLE DOCTORS IN OUR SYSTEM:"]
    for spec, doctors in sorted(by_spec.items()):
        doctors_str = ", ".join(doctors)
        lines.append(f"- {spec}: {doctors_str}")
    
    return "\n".join(lines)

def should_use_summary_agent(message: str) -> bool:
    """
    Determines if the user message requires the Summary Agent.
    """
    msg_lower = message.lower()
    return any(keyword in msg_lower for keyword in SUMMARY_AGENT_KEYWORDS)

def get_available_specializations() -> list:
    """
    Returns list of all specializations available in the database.
    """
    db = sqlite3.connect(DB_PATH)
    cur = db.cursor()
    query = "SELECT DISTINCT specialization FROM doctors"
    result = cur.execute(query)
    specs = [row[0] for row in result.fetchall()]
    db.close()
    return specs

def get_all_doctor_names() -> list:
    """
    Returns list of all doctor names in the database.
    """
    db = sqlite3.connect(DB_PATH)
    cur = db.cursor()
    query = "SELECT name FROM doctors"
    result = cur.execute(query)
    names = [row[0] for row in result.fetchall()]
    db.close()
    return names

def extract_mentioned_doctors_from_history(chat_history: list) -> list:
    """
    Extracts doctor names mentioned in the last assistant message.
    Returns a list of doctor names found, or empty list if none.
    """
    all_doctors = get_all_doctor_names()
    mentioned_doctors = []
    
    # Cerca solo nell'ultimo messaggio dell'assistente
    for entry in reversed(chat_history):
        if entry.get("role") == "assistant":
            content = entry.get("content", "")
            # Cerca ogni nome di dottore nel messaggio
            for doctor_name in all_doctors:
                if doctor_name.lower() in content.lower():
                    mentioned_doctors.append(doctor_name)
            break  # Solo l'ultimo messaggio dell'assistente
    
    return mentioned_doctors

def get_slots_by_doctors(doctor_names: list) -> list:
    """
    Gets available slots filtered by specific doctor names.
    Returns list of slots for the specified doctors.
    """
    if not doctor_names:
        return []
    
    db = sqlite3.connect(DB_PATH)
    cur = db.cursor()
    
    # Costruisci query con OR per ogni dottore
    placeholders = " OR ".join(["LOWER(a.doctor) = LOWER(?)"] * len(doctor_names))
    query = f"""
        SELECT a.id, a.doctor, a.time_slot, d.specialization
        FROM appointments a
        JOIN doctors d ON a.doctor = d.name
        WHERE a.patient IS NULL AND ({placeholders})
        ORDER BY a.time_slot
    """
    
    result = cur.execute(query, doctor_names)
    rows = result.fetchall()
    db.close()
    
    return rows

def get_slots_by_specialization(specialization: str | None) -> str:
    """
    Gets available slots filtered by specialization.
    If specialization is None, returns all available slots.
    """
    db = sqlite3.connect(DB_PATH)
    cur = db.cursor()
    
    if specialization:
        query = """
            SELECT a.id, a.doctor, a.time_slot, d.specialization
            FROM appointments a
            JOIN doctors d ON a.doctor = d.name
            WHERE a.patient IS NULL AND LOWER(d.specialization) = LOWER(?)
            ORDER BY a.time_slot
        """
        result = cur.execute(query, (specialization,))
    else:
        query = """
            SELECT a.id, a.doctor, a.time_slot, d.specialization
            FROM appointments a
            JOIN doctors d ON a.doctor = d.name
            WHERE a.patient IS NULL
            ORDER BY d.specialization, a.time_slot
        """
        result = cur.execute(query)
    
    rows = result.fetchall()
    db.close()
    
    return rows

# =============================================================================
# WEBSOCKET CHAT (with automatic router)
# =============================================================================
@sock.route("/ws")
def chat_socket(ws):
    """
    WebSocket endpoint for real-time chat.
    
    Note: WebSockets can't access Flask sessions directly, so we get the 
    username from a query parameter (e.g., /ws?username=John%20Doe).
    The frontend must pass the username when connecting.
    """
    chat_history = []
    sql_chat_history = []
    cid = id(ws)
    active_connections[cid] = chat_history
    
    # Get username from query parameter
    from urllib.parse import parse_qs
    
    current_ws_user_name = USER_NAME  # Default fallback from config
    
    try:
        # Parse query string to get username
        query_string = ws.environ.get('QUERY_STRING', '')
        query_params = parse_qs(query_string)
        
        # Get username from query params (e.g., ?username=John%20Doe)
        username_param = query_params.get('username', [None])[0]
        print("the username_param is",query_params.get('username', [None]))
        if username_param:
            current_ws_user_name = username_param
            print(f"WebSocket: Connected user: {current_ws_user_name}")
            sql_agent = initialize_sql_agent(current_ws_user_name, max_tokens=MAX_TOKENS, temp=T)
            agent = initialize_llm(current_ws_user_name, HOST, k=K, max_tokens=MAX_TOKENS, temp=T)

        else:
            print("WebSocket: No username provided, using default")
    except Exception as e:
        print(f"WebSocket error: {e}")
    
    # Ensure chat history file exists for this user
    ensure_user_chat_history_exists(current_ws_user_name)

    ws.send("Bot: Hello! I'm ready to assist you. I can help with medical questions and manage your appointments.")

    try:
        while True:
            msg = ws.receive()
            if msg is None:
                break

            # Save user message to file
            save_chat_message("user", msg, current_ws_user_name)

            try:
                # Router by keywords
                if should_use_summary_agent(msg):
                    # Usa Summary Agent 
                    response = generate_consultation_summary(summary_llm, current_ws_user_name)
                # Usa SQL Agent 
                elif should_use_sql_agent(msg):                    
                    print("Routing to SQL Agent")
                    
                    # Se l'utente chiede "show slots" o "available"
                    msg_lower = msg.lower()
                    if any(kw in msg_lower for kw in ["slot", "available", "show", "see"]):
                        # Estrai i medici menzionati nell'ultimo messaggio dell'assistente
                        mentioned_doctors = extract_mentioned_doctors_from_history(chat_history)
                        print(f"Doctors mentioned in last response: {mentioned_doctors}")
                        
                        if mentioned_doctors:
                            # Mostra solo gli slot dei medici menzionati
                            slots = get_slots_by_doctors(mentioned_doctors)
                            
                            if slots:
                                doctors_str = ", ".join(mentioned_doctors)
                                slots_info = f"AVAILABLE SLOTS FOR {doctors_str}:\n"
                                for slot in slots:
                                    slot_id, doctor, time_slot, spec = slot
                                    slots_info += f"- Slot ID {slot_id}: {doctor} ({spec}) - {time_slot}\n"
                            else:
                                # Nessuno slot per quei medici, mostra tutti
                                all_slots = get_slots_by_specialization(None)
                                doctors_str = ", ".join(mentioned_doctors)
                                if all_slots:
                                    slots_info = f"No slots available for {doctors_str}. Here are ALL available slots:\n"
                                    for slot in all_slots:
                                        slot_id, doctor, time_slot, spec = slot
                                        slots_info += f"- Slot ID {slot_id}: {doctor} ({spec}) - {time_slot}\n"
                                else:
                                    slots_info = "No appointment slots available at the moment."
                        else:
                            # Nessun medico menzionato, mostra tutti gli slot
                            all_slots = get_slots_by_specialization(None)
                            if all_slots:
                                slots_info = "ALL AVAILABLE SLOTS:\n"
                                for slot in all_slots:
                                    slot_id, doctor, time_slot, spec = slot
                                    slots_info += f"- Slot ID {slot_id}: {doctor} ({spec}) - {time_slot}\n"
                            else:
                                slots_info = "No appointment slots available at the moment."
                        
                        context_prefix = f"[PRE-FETCHED SLOTS DATA - USE THIS EXACTLY, DO NOT QUERY AGAIN]:\n{slots_info}\n\nUser says: "
                        message_for_agent = context_prefix + msg
                        
                        sql_chat_history.append({"role": "user", "content": message_for_agent})
                        if len(sql_chat_history) > CHAT_BUFFER:
                            sql_chat_history[:] = sql_chat_history[-CHAT_BUFFER:]
                        
                        sql_result = sql_agent.invoke({"messages": sql_chat_history})
                        sql_chat_history, response = parse_results(sql_result)
                        sql_chat_history.append({"role": "assistant", "content": response})
                else:
                    # Usa LLM Agent per domande mediche
                    # Recupera la lista completa dei medici dal database
                    doctors_list = get_all_doctors_list()

                    # --- INTEGRAZIONE RETRIEVER SINTOMI ---
                    # Recupera informazioni mediche dalla knowledge base FAISS sui sintomi inseriti dall'utente
                    faiss_context = None
                    if doc_retriever is not None and msg.strip():
                        faiss_context = search_medical_info(doc_retriever, msg)

                    # Costruisci il prompt arricchito
                    enhanced_msg = f"{msg}\n\n[SYSTEM - DOCTORS DATABASE]:\n{doctors_list}\n\n"
                    if faiss_context and 'No relevant' not in faiss_context:
                        enhanced_msg += f"[SYSTEM - MEDICAL KNOWLEDGE BASE]:\n{faiss_context}\n\n"
                    print("the enhanced_msg",enhanced_msg)
                    enhanced_msg += "INSTRUCTIONS: Based on the user's symptoms, choose the most appropriate doctor from the list above and give him a hint base on the symptoms and medical knowledge base."

                    chat_history.append({"role": "user", "content": enhanced_msg})
                    if len(chat_history) > CHAT_BUFFER:
                        chat_history[:] = chat_history[-CHAT_BUFFER:]

                    llm_result = agent.invoke({"messages": chat_history})
                    chat_history, response = parse_results(llm_result)
                    chat_history.append({"role": "assistant", "content": response})

                # Save bot response to file
                save_chat_message("bot", response, current_ws_user_name)
                ws.send(response)

            except Exception as e:
                ws.send(f"Bot Error: {str(e)}")

    finally:
        active_connections.pop(cid, None)
        print("WebSocket disconnected")


# ======================================================
# Chat history download & view
# ======================================================
@app.get("/history")
@login_required
def download_history():
    print("GET /history called")
    current_user_name = g.current_user['full_name']
    path = os.path.join(CHAT_HISTORY_FOLDER, f"{current_user_name.lower()}.txt")
    if not os.path.exists(path):
        return jsonify({"error": "No history found"}), 404

    return send_file(
        path,
        as_attachment=True,
        download_name=f"{current_user_name}_chat_history.txt",
        mimetype="text/plain"
    )



@app.get("/api/my-reservations")
@login_required
def api_my_reservations():
    """
    API endpoint to get user's reservations as JSON.
    """
    print("GET /api/my-reservations called")
    
    # Get the authenticated user's name
    current_user_name = g.current_user['full_name']
    
    db = sqlite3.connect(DB_PATH)
    cur = db.cursor()
    
    query = """
        SELECT a.id, a.doctor, a.time_slot, d.specialization
        FROM appointments a
        JOIN doctors d ON a.doctor = d.name
        WHERE LOWER(a.patient) = LOWER(?)
        ORDER BY a.time_slot
    """
    
    result = cur.execute(query, (current_user_name,))
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
    
    return jsonify({'reservations': reservations, 'user_name': current_user_name})






@app.get("/api/doctors")
def api_doctors():
    """
    API endpoint to get all doctors and their available slots as JSON.
    """
    print("GET /api/doctors called")
    
    db = sqlite3.connect(DB_PATH)
    cur = db.cursor()
    
    # Get all doctors
    doctors_query = "SELECT name, specialization FROM doctors ORDER BY name"
    doctors_result = cur.execute(doctors_query).fetchall()
    
    doctors = []
    for doc in doctors_result:
        # Get available slots for each doctor
        slots_query = """
            SELECT id, time_slot 
            FROM appointments 
            WHERE doctor = ? AND patient IS NULL
            ORDER BY time_slot
        """
        slots_result = cur.execute(slots_query, (doc[0],)).fetchall()
        
        doctors.append({
            'name': doc[0],
            'specialization': doc[1],
            'slots': [{'id': s[0], 'time_slot': s[1]} for s in slots_result]
        })
    
    db.close()
    
    return jsonify({'doctors': doctors, 'user_name': get_current_user_name()})


@app.get("/api/chat-history")
@login_required
def api_chat_history():
    """
    API endpoint to get chat history as JSON.
    """
    print("GET /api/chat-history called")
    
    # Get the authenticated user's name
    current_user_name = g.current_user['full_name']
    
    path = os.path.join(CHAT_HISTORY_FOLDER, f"{current_user_name.lower()}.txt")
    
    messages = []
    if os.path.exists(path):
        import re
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
            # Parse messages with format: [DD-MM-YYYY HH:MM:SS] role: message
            pattern = r'\[(\d{2}-\d{2}-\d{4} \d{2}:\d{2}:\d{2})\] (user|bot): (.+?)(?=\n\[|\Z)'
            matches = re.findall(pattern, content, re.DOTALL)
            
            for match in matches:
                timestamp, role, text = match
                messages.append({
                    'timestamp': timestamp,
                    'role': 'user' if role == 'user' else 'bot',
                    'text': text.strip()
                })
    
    return jsonify({'messages': messages, 'user_name': current_user_name})


@app.post("/api/book-slot/<int:slot_id>")
@login_required
def api_book_slot(slot_id):
    """
    API endpoint to book a slot from the doctors page.
    """
    print(f"POST /api/book-slot/{slot_id} called")
    
    # Get the authenticated user's name
    current_user_name = g.current_user['full_name']
    
    data = request.get_json() or {}
    patient = data.get('patient', current_user_name)
    
    db = sqlite3.connect(DB_PATH)
    cur = db.cursor()
    
    # Check if slot exists and is available
    check_query = "SELECT id, patient FROM appointments WHERE id = ?"
    result = cur.execute(check_query, (slot_id,)).fetchone()
    print("slot_id,result", slot_id, result)
    if not result:
        db.close()
        return jsonify({"error": "Slot not found"}), 404
    
    if result[1] is not None:
        db.close()
        return jsonify({"error": "Slot already booked"}), 400
    
    # Book the slot
    update_query = "UPDATE appointments SET patient = ? WHERE id = ?"
    cur.execute(update_query, (patient, slot_id))
    db.commit()
    db.close()
    
    return jsonify({"success": True, "message": "Appointment booked successfully"})


@app.post("/api/cancel-slot/<int:slot_id>")
@login_required
def api_cancel_slot(slot_id):
    """
    API endpoint to cancel a reservation.
    """
    print(f"POST /api/cancel-slot/{slot_id} called")
    
    # Get the authenticated user's name
    current_user_name = g.current_user['full_name']
    
    data = request.get_json() or {}
    patient = data.get('patient', current_user_name)
    
    db = sqlite3.connect(DB_PATH)
    cur = db.cursor()
    
    # Check if slot exists and belongs to this patient
    check_query = "SELECT id, patient, doctor, time_slot FROM appointments WHERE id = ?"
    result = cur.execute(check_query, (slot_id,)).fetchone()
    print("slot_id,result,patient", slot_id, result,patient)
    if not result:
        db.close()
        return jsonify({"error": "Slot not found"}), 404
    
    if result[1] is None:
        db.close()
        return jsonify({"error": "Slot is not booked"}), 400
    
    if result[1].lower() != patient.lower():
        db.close()
        return jsonify({"error": "Cannot cancel another patient's reservation"}), 403
    
    doctor = result[2]
    time_slot = result[3]
    
    # Cancel the reservation
    update_query = "UPDATE appointments SET patient = NULL WHERE id = ?"
    cur.execute(update_query, (slot_id,))
    db.commit()
    db.close()
    
    return jsonify({
        "success": True, 
        "message": f"Appointment with {doctor} for {time_slot} cancelled successfully"
    })


# ======================================================
# Document Upload Endpoints
# ======================================================
@app.post("/api/upload-document")
@login_required
def upload_document():
    """
    API endpoint to upload a document (image, PDF, etc.).
    Saves file and stores metadata in documents table.
    """
    print("POST /api/upload-document called")
    
    # Get the authenticated user's name
    current_user_name = g.current_user['full_name']
    
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400
    
    file = request.files['file']
    description = request.form.get('description', '')
    
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400
    
    if not allowed_file(file.filename):
        return jsonify({"error": f"File type not allowed. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"}), 400
    
    # Check file size
    file.seek(0, 2)  # Seek to end
    file_size = file.tell()
    file.seek(0)  # Reset to beginning
    if file_size > MAX_FILE_SIZE:
        return jsonify({"error": f"File too large. Maximum size is 2MB. Your file: {file_size / (1024 * 1024):.2f}MB"}), 400
    
    # Create unique filename with timestamp
    filename = secure_filename(file.filename)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_filename = f"{current_user_name.lower()}_{timestamp}_{filename}"
    file_path = os.path.join(UPLOAD_FOLDER, unique_filename)
    
    # Save the file
    file.save(file_path)
    
    # Store in database
    db = sqlite3.connect(DB_PATH)
    cur = db.cursor()
    
    # Ensure documents table exists (in case DB was created before this feature)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id TEXT,
            patient_surname TEXT,
            document_path TEXT,
            upload_date TEXT,
            description TEXT
        )
    """)
    
    insert_query = """
        INSERT INTO documents (patient_id, patient_surname, document_path, upload_date, description)
        VALUES (?, ?, ?, ?, ?)
    """
    upload_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur.execute(insert_query, (current_user_name.lower(), current_user_name, file_path, upload_date, description))
    doc_id = cur.lastrowid
    db.commit()
    db.close()
    
    return jsonify({
        "success": True, 
        "message": "Document uploaded successfully",
        "document_id": doc_id,
        "filename": unique_filename,
        "file_path": file_path
    })


@app.get("/api/my-documents")
@login_required
def get_my_documents():
    """
    Returns list of documents uploaded by the current user.
    """
    print("GET /api/my-documents called")
    
    # Get the authenticated user's name
    current_user_name = g.current_user['full_name']
    
    db = sqlite3.connect(DB_PATH)
    cur = db.cursor()
    
    # Ensure table exists
    cur.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id TEXT,
            patient_surname TEXT,
            document_path TEXT,
            upload_date TEXT,
            description TEXT
        )
    """)
    
    query = """
        SELECT id, patient_surname, document_path, upload_date, description
        FROM documents
        WHERE LOWER(patient_id) = LOWER(?)
        ORDER BY upload_date DESC
    """
    result = cur.execute(query, (current_user_name,)).fetchall()
    db.close()
    
    documents = [
        {
            'id': r[0],
            'patient_surname': r[1],
            'filename': os.path.basename(r[2]),
            'upload_date': r[3],
            'description': r[4]
        }
        for r in result
    ]
    
    return jsonify({"documents": documents})


@app.post("/api/analyze-lab-report")
@login_required
def analyze_lab_report_endpoint():
    """
    API endpoint to analyze a laboratory report PDF.
    Uses the Document Agent to extract values and provide medical advice.
    """
    print("POST /api/analyze-lab-report called")
    
    if document_llm is None or doc_retriever is None:
        return jsonify({
            "success": False,
            "error": "Document analysis is not available. PDF library not installed."
        }), 503
    
    data = request.get_json()
    if not data or 'file_path' not in data:
        return jsonify({"error": "No file_path provided"}), 400
    
    file_path = data['file_path']
    
    if not os.path.exists(file_path):
        return jsonify({"error": "File not found"}), 404
    
    if not file_path.lower().endswith('.pdf'):
        return jsonify({"error": "Only PDF files can be analyzed"}), 400
    
    try:
        # Analyze the lab report using the Document Agent
        print("line 1315",g.current_user)
        analysis_result = analyze_lab_report(document_llm, doc_retriever, file_path)
        
        # Save the analysis to chat history
        
        save_chat_message("bot", f"Lab Report Analysis:\n{analysis_result}",g.current_user['full_name'])
        
        return jsonify({
            "success": True,
            "analysis": analysis_result
        })
    except Exception as e:
        print(f"Error analyzing lab report: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"Error analyzing report: {str(e)}"
        }), 500


@app.delete("/api/document/<int:doc_id>")
def delete_document(doc_id):
    """
    Deletes a document by ID (only if owned by current user).
    """
    print(f"DELETE /api/document/{doc_id} called")
    
    db = sqlite3.connect(DB_PATH)
    cur = db.cursor()
    
    # Check ownership
    check_query = "SELECT document_path, patient_id FROM documents WHERE id = ?"
    result = cur.execute(check_query, (doc_id,)).fetchone()
    
    if not result:
        db.close()
        return jsonify({"error": "Document not found"}), 404
    
    if result[1].lower() != USER_NAME.lower():
        db.close()
        return jsonify({"error": "Not authorized"}), 403
    
    # Delete file from disk
    file_path = result[0]
    if os.path.exists(file_path):
        os.remove(file_path)
    
    # Delete from database
    cur.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
    db.commit()
    db.close()
    
    return jsonify({"success": True, "message": "Document deleted successfully"})


# ======================================================
# Database helpers
# ======================================================
def retrieve_appointment(slot_id: int):
    with sqlite3.connect("assets/database/medassist.db") as db:
        cur = db.cursor()
        cur.execute(
            "SELECT doctor, time_slot, patient FROM appointments WHERE id=?",
            (slot_id,),
        )
        return cur.fetchone()

def set_appointment(patient, slot_id: int):
    with sqlite3.connect("assets/database/medassist.db") as db:
        cur = db.cursor()
        cur.execute("UPDATE appointments SET patient=? WHERE id=?", (patient, slot_id))
        db.commit()

# ======================================================
# CRUD endpoints
# ======================================================
@app.get("/res")
def get_reservation():
    print("GET /res called")
    slot_id = request.args.get("id", type=int)
    if not slot_id:
        return jsonify({"error": "Missing slot_id"}), 400

    row = retrieve_appointment(slot_id)
    if not row:
        return jsonify({"error": "Not found"}), 404

    doctor, time_slot, patient = row
    return jsonify({
        "slot_id": slot_id,
        "doctor": doctor,
        "time_slot": time_slot,
        "status": "reserved" if patient else "available"
    })

@app.post("/setReservation")
def reserve():
    data = request.get_json(silent=True) or {}
    slot_id = data.get("slot_id") or request.args.get("slot_id", type=int)
    if not slot_id:
        return jsonify({"response": "Missing slot_id"}), 400

    row = retrieve_appointment(slot_id)
    if not row:
        return jsonify({"response": "Unable to process request"}), 404

    _, _, patient = row
    if patient and patient.lower() != USER_NAME.lower():
        return jsonify({"response": "Unable to process request"}), 403

    if not patient:
        set_appointment(USER_NAME, slot_id)

    return jsonify({"response": "Reservation successful"})

@app.post("/cancelReservation")
def cancel():
    print("POST /cancelReservation called")
    data = request.get_json(silent=True) or {}
    slot_id = data.get("slot_id") or request.args.get("slot_id", type=int)
    if not slot_id:
        return jsonify({"response": "Missing slot_id"}), 400

    row = retrieve_appointment(slot_id)
    if not row:
        return jsonify({"response": "Unable to process request"}), 404

    _, _, patient = row
    if patient and patient.lower() != USER_NAME.lower():
        return jsonify({"response": "Unable to process request"}), 403

    set_appointment(None, slot_id)
    return jsonify({"response": "Cancellation successful"})

# ======================================================
# Health check
# ======================================================
@app.get("/health")
def health():
    return {"status": "ok"}

# ======================================================
# Run server
# ======================================================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
