# HealthAssistant

# Project Overview

## What is HealthAssistant?

**HealthAssistant** is a full-stack web application that combines:
- A **medical chatbot** powered by LLM (Large Language Model) Llama 3.1
- An **appointment booking system** with doctors
- A **medical portal** for doctors to view patients and histories
- **Lab report analysis** (PDF) with AI
- The ability for users to request a summary of their chat/consultation at any time

## Tecnical Info

| Component | Tecnology |
|------------|------------|
| **Backend** | Python 3.10, Flask |
| **Frontend** | React 18 |
| **Database** | SQLite3 |
| **LLM** | Ollama with Llama 3.1 |
| **Embeddings** | HuggingFace sentence-transformers/all-MiniLM-L6-v2 |
| **Vector Store** | FAISS (Facebook AI Similarity Search) |
| **Framework AI** | LangChain, LangGraph |


## Features

- Users can request a summary of their chat at any time, receiving a concise recap of symptoms, advice, and booked appointments.

### Symptom checker and chatbot for medical advice
- Provides instant responses to user symptoms and health questions.
- After describing symptoms, the user receives practical advice and, if appropriate, a recommendation for a specialist based on the doctors available in the database. The user can then book an appointment with the suggested specialist either via chatbot or through the graphical interface.

[![Symptom Checker Demo](assets/symptom_checker_thumbnail.png)](https://github.com/TiloccaS/HealthAssistant/video/medical_knowledge.mp4)

### Lab report analysis with abnormal value detection
- The user can upload a lab report file. The system checks if the file is a PDF and smaller than 2MB. Only valid PDF files trigger the lab report analysis agent.
- If the file is a valid medical lab report, the agent can summarize or help interpret the results, highlighting abnormal values.
- If the uploaded PDF is not a medical report, the agent notifies the user.
- Users can upload other file types, but only PDF files activate the lab report analysis feature.

[![Lab Report Analysis Demo](assets/lab_report_analysis_thumbnail.png)](https://github.com/TiloccaS/HealthAssistant/video/analyze_lab_report.mp4)


### Doctor and patient dashboards
- Custom dashboards for doctors and patients to manage appointments, view records, and more.
- After a patient books an appointment, the doctor can see the list of their booked patients. Initially, the patient's main problem is not described.
- The doctor can request a summary of the patient's main health issue, which is automatically extracted from the chat history by a dedicated agent.
- Doctors also have access to the full chat history with each patient for better context and follow-up.

[![Dashboard Demo](assets/dashboard_thumbnail.png)](https://github.com/TiloccaS/HealthAssistant/video/book_appointment_doctor_dashboard.mp4)

### Appointment booking system
- Book, view, and manage appointments with available doctors. Users can also manage appointments directly via chat: view available slots for a specific doctor, book a specific slot, view their own reservations, or cancel existing bookings.
[![Appointment Booking Demo](assets/appointment_booking_thumbnail.png)](https://github.com/TiloccaS/HealthAssistant/video/query_by_chatbot.mp4)



## Folder Structure

```
HealthAssistant/
├── app.py                 # Main Flask backend
├── config.py              # Global configuration
├── src/                   # Python modules
│   ├── __init__.py        # Module exports
│   ├── auth.py            # Authentication system
│   ├── helper.py          # Main LLM agent
│   ├── sql_agent.py       # Appointment agent
│   ├── summary_agent.py   # Summary agent
│   ├── document_agent.py  # PDF analysis agent
│   └── prompt.py          # Prompt templates
├── frontend/              # React application
│   ├── src/
│   │   ├── App.jsx        # Main component
│   │   ├── context/       # React context
│   │   ├── pages/         # App pages
│   │   └── Components/    # Reusable components
├── assets/                # Static files
   ├── database/          # SQLite database
   ├── index/             # FAISS index
   ├── chat_history/      # User chat history
   └── uploads/           # Uploaded files
```



1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/HealthAssistant.git
   cd HealthAssistant
   ```

2. **Set up Python environment:**
   ```bash
   conda create -n health_assistant python=3.10
   conda activate health_assistant
   pip install -r requirements.txt
   ```

3. **Set up frontend:**
   ```bash
   cd frontend
   npm install
   ```

4. **Install Ollama and download llama3.1 model:**
   - Download and install Ollama from [https://ollama.com/download](https://ollama.com/download) for your operating system.
   - After installation, run:
     ```bash
     ollama pull llama3.1
     ```
5. **Download medical datasets for RAG:**
    - Download MedQuAD from [https://github.com/abachaa/MedQuAD](https://github.com/abachaa/MedQuAD)
       - Unzip and place the folder as:
          `HealthAssistant/src/data/MedQuAD-master`
    - Download MIMIC-III demo from [https://physionet.org/content/mimiciii-demo/get-zip/1.4/](https://physionet.org/content/mimiciii-demo/get-zip/1.4/)
       - Unzip and place the folder as:
          `HealthAssistant/src/data/MIMIC-III/mimiciii-demo/demo`

6. **Create the vector store for medical RAG:**
    - Run the following command from the project root:
       ```bash
       python src/create_index.py
       ```
7. **Create the database:**
    - Run the following command from the project root:
       ```bash
       python src/init_db.py
       ```

## Running the Application

1. **Start the backend (port 8080):**
   ```bash
   python app.py
   ```
   Wait until you see the message indicating the backend is running and fully initialized on port 8080.

2. **Start the frontend:**
   ```bash
   cd frontend
   npm run dev
   ```

3. **Access the app:**
   Open [http://localhost:5173](http://localhost:5173) in your browser.
