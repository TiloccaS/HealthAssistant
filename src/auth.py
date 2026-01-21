"""
Authentication Module for MedAssistant
======================================

This module handles user authentication using Flask's built-in session system.
Sessions are stored in signed cookies (no database table needed for sessions).

How it works:
1. User sends username + password to /api/auth/login
2. Server verifies password against database
3. If correct, server stores user_id in Flask session (a signed cookie)
4. On every request, we read user_id from session cookie to identify user
5. On logout, we clear the session cookie

This is simpler than token-based auth because Flask handles cookie signing.
"""

import re
import sqlite3
import hashlib
import secrets
from functools import wraps
from flask import request, jsonify, g, session

from config import DB_PATH


# =============================================================================
# PASSWORD FUNCTIONS
# =============================================================================

def hash_password(password: str, salt: str = None) -> tuple:
    """
    Hash a password securely using PBKDF2-SHA256.
    
    Why PBKDF2?
    - It's intentionally slow (100,000 iterations) to make brute-force attacks hard
    - The salt prevents rainbow table attacks
    
    Args:
        password: The plain text password
        salt: Random string to add uniqueness (generated if not provided)
    
    Returns:
        Tuple of (hashed_password, salt) - both as hex strings
    """
    # Generate random salt if not provided
    if salt is None:
        salt = secrets.token_hex(32)
    
    # Hash password with salt using 100,000 iterations
    hashed = hashlib.pbkdf2_hmac(
        'sha256',           # Hash algorithm
        password.encode(),  # Password as bytes
        salt.encode(),      # Salt as bytes
        100000              # Number of iterations (higher = slower = more secure)
    )
    
    return hashed.hex(), salt


def verify_password(password: str, stored_hash: str, salt: str) -> bool:
    """
    Check if a password matches the stored hash.
    
    Args:
        password: The password to check
        stored_hash: The hash stored in database
        salt: The salt stored in database
    
    Returns:
        True if password is correct, False otherwise
    """
    # Hash the provided password with the same salt
    computed_hash, _ = hash_password(password, salt)
    
    # Compare using constant-time comparison (prevents timing attacks)
    return secrets.compare_digest(computed_hash, stored_hash)


def validate_password_strength(password: str) -> tuple:
    """
    Check if password meets security requirements.
    
    Requirements:
    - At least 8 characters
    - At least one uppercase letter
    - At least one lowercase letter  
    - At least one number
    - At least one special character
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters"
    
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain an uppercase letter"
    
    if not re.search(r'[a-z]', password):
        return False, "Password must contain a lowercase letter"
    
    if not re.search(r'\d', password):
        return False, "Password must contain a number"
    
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False, "Password must contain a special character"
    
    return True, None


def validate_email(email: str) -> bool:
    """Check if email format is valid."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


# =============================================================================
# USER REGISTRATION
# =============================================================================

def register_user(username: str, email: str, password: str, full_name: str, 
                  role: str = 'patient') -> tuple:
    """
    Create a new user account in the database.
    
    Args:
        username: Unique username (min 3 chars)
        email: Valid email address
        password: Password meeting strength requirements
        full_name: User's display name
        role: 'patient', 'doctor', or 'admin'
    
    Returns:
        Tuple of (success, user_id or error_message)
    """
    # Validate all inputs
    if not username or len(username) < 3:
        return False, "Username must be at least 3 characters"
    
    if not validate_email(email):
        return False, "Invalid email format"
    
    is_valid, error = validate_password_strength(password)
    if not is_valid:
        return False, error
    
    if not full_name or len(full_name) < 2:
        return False, "Full name is required"
    
    if role not in ['patient', 'doctor', 'admin']:
        return False, "Invalid role"
    
    # Hash the password before storing
    password_hash, salt = hash_password(password)
    
    # Connect to database
    db = sqlite3.connect(DB_PATH)
    cur = db.cursor()
    
    try:
        # Check if username already exists
        cur.execute("SELECT id FROM users WHERE LOWER(username) = LOWER(?)", (username,))
        if cur.fetchone():
            db.close()
            return False, "Username already exists"
        
        # Check if email already exists
        cur.execute("SELECT id FROM users WHERE LOWER(email) = LOWER(?)", (email,))
        if cur.fetchone():
            db.close()
            return False, "Email already registered"
        
        # Insert new user
        cur.execute("""
            INSERT INTO users (username, email, password_hash, password_salt, role, full_name)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (username.lower(), email.lower(), password_hash, salt, role, full_name))
        
        user_id = cur.lastrowid
        db.commit()
        db.close()
        
        return True, user_id
        
    except sqlite3.IntegrityError as e:
        db.close()
        return False, f"Database error: {str(e)}"


# =============================================================================
# USER LOGIN
# =============================================================================

def login_user(username_or_email: str, password: str) -> tuple:
    """
    Authenticate user and create session.
    
    Args:
        username_or_email: Can be either username or email
        password: User's password
    
    Returns:
        Tuple of (success, error_message, user_info_dict)
    """
    db = sqlite3.connect(DB_PATH)
    cur = db.cursor()
    
    # Find user by username OR email
    query = """
        SELECT id, username, email, password_hash, password_salt, role, full_name
        FROM users
        WHERE LOWER(username) = LOWER(?) OR LOWER(email) = LOWER(?)
    """
    result = cur.execute(query, (username_or_email, username_or_email)).fetchone()
    #it extract the user info from the database if the username or email matches
    # User not found
    if not result:
        db.close()
        return False, "Invalid username or password", None
    
    user_id, username, email, stored_hash, salt, role, full_name = result
    
    # Wrong password
    if not verify_password(password, stored_hash, salt):#it checks if the password is correct
        db.close()
        return False, "Invalid username or password", None
    
    db.close()
    
    # Store user_id in Flask session (this creates a signed cookie)
    session['user_id'] = user_id
    session.permanent = True  # Session lasts until browser closes or expires
    
    # Return user info
    user_info = {
        'user_id': user_id,
        'username': username,
        'email': email,
        'role': role,
        'full_name': full_name
    }
    
    return True, None, user_info


def logout_user():
    """
    Log out the current user by clearing the session.
    """
    session.clear()


# =============================================================================
# GET CURRENT USER
# =============================================================================

def get_current_user():
    """
    Get the currently logged-in user from the session cookie.
    
    Returns:
        User info dict if logged in, None otherwise
    """
    # Check if user_id is in session
    user_id = session.get('user_id')
    print("the user id is:",user_id)
    if not user_id:
        return None
    
    # Get user from database
    return get_user_by_id(user_id)


def get_user_by_id(user_id: int) -> dict:
    """
    Get user info from database by ID.
    
    Args:
        user_id: The user's database ID
    
    Returns:
        User info dict or None if not found
    """
    db = sqlite3.connect(DB_PATH)
    cur = db.cursor()
    
    query = "SELECT id, username, email, role, full_name FROM users WHERE id = ?"
    result = cur.execute(query, (user_id,)).fetchone()
    db.close()
    
    if not result:
        return None
    
    return {
        'user_id': result[0],
        'username': result[1],
        'email': result[2],
        'role': result[3],
        'full_name': result[4]
    }


def get_doctor_for_user(user_id: int) -> dict:
    """
    Get doctor profile linked to a user account.
    
    Args:
        user_id: The user's database ID
    
    Returns:
        Doctor info dict or None if user is not a doctor
    """
    db = sqlite3.connect(DB_PATH)
    cur = db.cursor()
    
    query = "SELECT name, specialization FROM doctors WHERE user_id = ?"
    result = cur.execute(query, (user_id,)).fetchone()
    db.close()
    
    if not result:
        return None
    
    return {
        'name': result[0],
        'specialization': result[1]
    }


# =============================================================================
# ROUTE DECORATORS (Protect endpoints)
# =============================================================================

def login_required(f):
    """
    Decorator that protects a route - only logged-in users can access.
    
    Usage:
        @app.get("/api/my-data")
        @login_required
        def get_my_data():
            user = g.current_user  # Access current user
            ...
    """
    @wraps(f)#f is the function decorated
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        print("Current user in login_required:",user)
        if not user:
            return jsonify({'error': 'Please log in first'}), 401
        
        # Store user in Flask's g object for easy access in route
        g.current_user = user
        return f(*args, **kwargs)
    return decorated_function


def doctor_required(f):
    """
    Decorator that allows only doctors (or admins) to access a route.
    
    Usage:
        @app.get("/api/doctor/patients")
        @login_required
        @doctor_required
        def get_patients():
            ...
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if not user:
            return jsonify({'error': 'Please log in first'}), 401
        
        if user['role'] not in ['doctor', 'admin']:
            return jsonify({'error': 'Doctor access required'}), 403
        
        g.current_user = user
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """
    Decorator that allows only admins to access a route.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if not user:
            return jsonify({'error': 'Please log in first'}), 401
        
        if user['role'] != 'admin':
            return jsonify({'error': 'Admin access required'}), 403
        
        g.current_user = user
        return f(*args, **kwargs)
    return decorated_function
