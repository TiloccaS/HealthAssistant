#!/usr/bin/env python3
"""
Standalone database initialization script.
Run this to create/reset the database with users and authentication.
"""

import os
import shutil
import sqlite3
import hashlib
import secrets
from datetime import datetime, timedelta

# Database path
DB_PATH = os.path.join(os.path.dirname(__file__), '../assets', 'database', 'medassist.db')


def hash_password(password, salt=None):
    if salt is None:
        salt = secrets.token_hex(32)
    hashed = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
    return hashed.hex(), salt


def init_database():
    print("=== MedAssistant Database Initialization ===\n")
    
    # Backup existing
    if os.path.exists(DB_PATH):
        backup_path = DB_PATH + '.old'
        shutil.move(DB_PATH, backup_path)
        print(f'Backed up existing database to {backup_path}')

    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Create tables
    cur.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        password_salt TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'patient',
        full_name TEXT NOT NULL
    )''')

    # Note: Sessions table not needed - we use Flask's built-in cookie sessions

    cur.execute('''CREATE TABLE IF NOT EXISTS doctors (
        name TEXT PRIMARY KEY,
        specialization TEXT NOT NULL,
        user_id INTEGER,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )''')

    cur.execute('''CREATE TABLE IF NOT EXISTS appointments (
        id INTEGER PRIMARY KEY,
        doctor TEXT NOT NULL,
        time_slot TEXT NOT NULL,
        patient TEXT,
        patient_problem TEXT,
        FOREIGN KEY (doctor) REFERENCES doctors(name)
    )''')

    cur.execute('''CREATE TABLE IF NOT EXISTS documents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id TEXT NOT NULL,
        patient_surname TEXT NOT NULL,
        document_path TEXT NOT NULL,
        upload_date TEXT NOT NULL,
        description TEXT
    )''')

    print('Tables created successfully')

    # Insert users
    users = [
        ('rossi', 'mario.rossi@email.com', 'Password123!', 'patient', 'Mario Rossi'),
        ('doe', 'john.doe@email.com', 'Password123!', 'patient', 'John Doe'),
        ('bianchi', 'luca.bianchi@email.com', 'Password123!', 'patient', 'Luca Bianchi'),
        ('verdi', 'anna.verdi@email.com', 'Password123!', 'patient', 'Anna Verdi'),
        ('martini', 'paolo.martini@email.com', 'Password123!', 'patient', 'Paolo Martini'),
        ('dr.fontana', 'fontana@medassist.com', 'DoctorPass123!', 'doctor', 'Dr. Fontana'),
        ('dr.moretti', 'moretti@medassist.com', 'DoctorPass123!', 'doctor', 'Dr. Moretti'),
        ('dr.ricci', 'ricci@medassist.com', 'DoctorPass123!', 'doctor', 'Dr. Ricci'),
        ('dr.colombo', 'colombo@medassist.com', 'DoctorPass123!', 'doctor', 'Dr. Colombo'),
        ('dr.ferrari', 'ferrari@medassist.com', 'DoctorPass123!', 'doctor', 'Dr. Ferrari'),
        ('dr.romano', 'romano@medassist.com', 'DoctorPass123!', 'doctor', 'Dr. Romano'),
        ('dr.greco', 'greco@medassist.com', 'DoctorPass123!', 'doctor', 'Dr. Greco'),
        ('dr.conti', 'conti@medassist.com', 'DoctorPass123!', 'doctor', 'Dr. Conti'),
        ('dr.mancini', 'mancini@medassist.com', 'DoctorPass123!', 'doctor', 'Dr. Mancini'),
        ('dr.barbieri', 'barbieri@medassist.com', 'DoctorPass123!', 'doctor', 'Dr. Barbieri'),
        ('admin', 'admin@medassist.com', 'AdminPass123!', 'admin', 'System Admin'),
    ]

    for username, email, password, role, full_name in users:
        pw_hash, salt = hash_password(password)
        cur.execute(
            'INSERT INTO users (username, email, password_hash, password_salt, role, full_name) VALUES (?, ?, ?, ?, ?, ?)',
            (username, email, pw_hash, salt, role, full_name)
        )

    print(f'Inserted {len(users)} users')

    # Insert doctors with user_id
    doctors = [
        ('Dr. Fontana', 'Neurology', 6),
        ('Dr. Moretti', 'Neurology', 7),
        ('Dr. Ricci', 'Pneumology', 8),
        ('Dr. Colombo', 'Cardiology', 9),
        ('Dr. Ferrari', 'Cardiology', 10),
        ('Dr. Romano', 'Dermatology', 11),
        ('Dr. Greco', 'Gastroenterology', 12),
        ('Dr. Conti', 'Endocrinology', 13),
        ('Dr. Mancini', 'Orthopedics', 14),
        ('Dr. Barbieri', 'Ophthalmology', 15),
    ]

    for name, spec, user_id in doctors:
        cur.execute('INSERT INTO doctors (name, specialization, user_id) VALUES (?, ?, ?)', (name, spec, user_id))

    print(f'Inserted {len(doctors)} doctors')

    # Insert appointments
    base_date = datetime.now() + timedelta(days=1)
    available_hours = [9, 10, 11, 14, 15, 16]
    sample_problems = [
        'Persistent headaches for the past 2 weeks',
        'Difficulty breathing during exercise',
        'Chest pain and palpitations',
    ]

    slot_id = 0
    for doc_idx, (doc_name, _, _) in enumerate(doctors):
        for day_offset in range(3):
            actual_day = (doc_idx % 5) + (day_offset * 5)
            slot_date = base_date + timedelta(days=actual_day)
            while slot_date.weekday() >= 5:
                slot_date += timedelta(days=1)
            day_hours = available_hours[day_offset::2]
            for hour in day_hours:
                time_slot = slot_date.replace(hour=hour, minute=0, second=0)
                time_str = time_slot.strftime('%d-%m-%Y %H:%M:%S')
                patient = None
                problem = None
                if slot_id == 2:
                    patient = 'Rossi'
                    problem = sample_problems[0]
                elif slot_id == 8:
                    patient = 'Bianchi'
                    problem = sample_problems[1]
                elif slot_id == 15:
                    patient = 'Verdi'
                    problem = sample_problems[2]
                cur.execute(
                    'INSERT INTO appointments (id, doctor, time_slot, patient, patient_problem) VALUES (?, ?, ?, ?, ?)',
                    (slot_id, doc_name, time_str, patient, problem)
                )
                slot_id += 1

    print(f'Inserted {slot_id} appointment slots')

    conn.commit()

    # Verify
    print('\n--- Database Verification ---')
    cur.execute('SELECT COUNT(*) FROM users')
    print(f'Users: {cur.fetchone()[0]}')
    cur.execute('SELECT COUNT(*) FROM doctors')
    print(f'Doctors: {cur.fetchone()[0]}')
    cur.execute('SELECT COUNT(*) FROM appointments')
    print(f'Appointments: {cur.fetchone()[0]}')
    cur.execute('SELECT COUNT(*) FROM appointments WHERE patient IS NOT NULL')
    print(f'Pre-booked: {cur.fetchone()[0]}')

    cur.execute('SELECT username, role, full_name FROM users ORDER BY role, username')
    print('\nRegistered Users:')
    for row in cur.fetchall():
        print(f'  - {row[0]} ({row[1]}): {row[2]}')

    conn.close()
    print(f'\nDatabase created at: {DB_PATH}')
    print('\n=== Initialization Complete ===')
    print('\nDemo Credentials:')
    print('  Patient: doe / Password123!')
    print('  Doctor:  dr.fontana / DoctorPass123!')
    print('  Admin:   admin / AdminPass123!')


if __name__ == '__main__':
    init_database()
