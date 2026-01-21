# HealthAssistant - Demo Credentials

## Patients

| Username | Email | Password | Full Name |
|----------|-------|----------|-----------|
| doe | john.doe@email.com | Password123! | John Doe |
| rossi | mario.rossi@email.com | Password123! | Mario Rossi |
| bianchi | luca.bianchi@email.com | Password123! | Luca Bianchi |
| verdi | anna.verdi@email.com | Password123! | Anna Verdi |
| martini | paolo.martini@email.com | Password123! | Paolo Martini |

## Doctors

| Username | Email | Password | Full Name | Specialization |
|----------|-------|----------|-----------|----------------|
| dr.fontana | fontana@medassist.com | DoctorPass123! | Dr. Fontana | Neurology |
| dr.moretti | moretti@medassist.com | DoctorPass123! | Dr. Moretti | Neurology |
| dr.ricci | ricci@medassist.com | DoctorPass123! | Dr. Ricci | Pneumology |
| dr.colombo | colombo@medassist.com | DoctorPass123! | Dr. Colombo | Cardiology |
| dr.ferrari | ferrari@medassist.com | DoctorPass123! | Dr. Ferrari | Cardiology |
| dr.romano | romano@medassist.com | DoctorPass123! | Dr. Romano | Dermatology |
| dr.greco | greco@medassist.com | DoctorPass123! | Dr. Greco | Gastroenterology |
| dr.conti | conti@medassist.com | DoctorPass123! | Dr. Conti | Endocrinology |
| dr.mancini | mancini@medassist.com | DoctorPass123! | Dr. Mancini | Orthopedics |
| dr.barbieri | barbieri@medassist.com | DoctorPass123! | Dr. Barbieri | Ophthalmology |

---

## Notes

- Passwords meet the following security requirements:
  - Minimum 8 characters
  - At least one uppercase letter
  - At least one lowercase letter
  - At least one number
  - At least one special character (!@#$%^&*...)

- To reinitialize the database with these credentials:
  ```bash
  python init_db.py
  ```

- Patients can access chat and appointment booking
- Doctors can access the doctor dashboard with patient list
