import React, { useState, useEffect } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

const API_BASE = `http://localhost:${import.meta.env.VITE_API_PORT || 8000}`;

const PatientDetail = () => {
  const { patientName } = useParams();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('overview');
  const [generatingProblem, setGeneratingProblem] = useState(null);
  
  const { logout, isDoctor } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (!isDoctor) {
      navigate('/login');
      return;
    }
    fetchPatientDetail();
  }, [isDoctor, navigate, patientName]);

  const fetchPatientDetail = async () => {
    try {
      // credentials: 'include' sends the session cookie automatically
      const response = await fetch(`${API_BASE}/api/doctor/patient/${encodeURIComponent(patientName)}`, {
        credentials: 'include'
      });
      
      if (!response.ok) {
        if (response.status === 401) {
          navigate('/login');
          return;
        }
        if (response.status === 404) {
          throw new Error('Patient not found');
        }
        throw new Error('Failed to fetch patient details');
      }
      
      const result = await response.json();
      setData(result);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  const handleGenerateProblem = async (appointmentId) => {
    setGeneratingProblem(appointmentId);
    try {
      const response = await fetch(`${API_BASE}/api/doctor/generate-problem/${appointmentId}`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' }
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to generate problem summary');
      }
      
      const result = await response.json();
      
      // Update the local state with the new problem
      setData(prevData => ({
        ...prevData,
        patient: {
          ...prevData.patient,
          appointments: prevData.patient.appointments.map(apt => 
            apt.slot_id === appointmentId 
              ? { ...apt, problem: result.patient_problem }
              : apt
          )
        }
      }));
    } catch (err) {
      alert(`Error: ${err.message}`);
    } finally {
      setGeneratingProblem(null);
    }
  };

  if (loading) {
    return (
      <div className="doctor-container">
        <div className="loading">
          <span className="spinner"></span>
          Loading patient details...
        </div>
        <style>{styles}</style>
      </div>
    );
  }

  if (error) {
    return (
      <div className="doctor-container">
        <header className="doctor-header">
          <div className="header-left">
            <span className="material-symbols-rounded logo-icon">medical_services</span>
            <h1>Doctor Portal</h1>
          </div>
          <div className="header-right">
            <button onClick={handleLogout} className="logout-btn">
              <span className="material-symbols-rounded">logout</span>
              Logout
            </button>
          </div>
        </header>
        <div className="error-page">
          <span className="material-symbols-rounded">error</span>
          <h2>{error}</h2>
          <Link to="/doctor/patients" className="back-btn">
            <span className="material-symbols-rounded">arrow_back</span>
            Back to Patients
          </Link>
        </div>
        <style>{styles}</style>
      </div>
    );
  }

  return (
    <div className="doctor-container">
      <header className="doctor-header">
        <div className="header-left">
          <span className="material-symbols-rounded logo-icon">medical_services</span>
          <h1>Doctor Portal</h1>
        </div>
        <div className="header-right">
          <span className="doctor-name">
            {data?.doctor?.name} - {data?.doctor?.specialization}
          </span>
          <button onClick={handleLogout} className="logout-btn">
            <span className="material-symbols-rounded">logout</span>
            Logout
          </button>
        </div>
      </header>

      <nav className="doctor-nav">
        <Link to="/doctor/dashboard" className="nav-item">
          <span className="material-symbols-rounded">dashboard</span>
          Dashboard
        </Link>
        <Link to="/doctor/patients" className="nav-item active">
          <span className="material-symbols-rounded">group</span>
          My Patients
        </Link>
        <Link to="/doctor/appointments" className="nav-item">
          <span className="material-symbols-rounded">calendar_month</span>
          Appointments
        </Link>
      </nav>

      <main className="doctor-main">
        <div className="breadcrumb">
          <Link to="/doctor/patients">
            <span className="material-symbols-rounded">arrow_back</span>
            Back to Patients
          </Link>
        </div>

        <div className="patient-header-card">
          <div className="patient-avatar-large">
            <span className="material-symbols-rounded">person</span>
          </div>
          <div className="patient-header-info">
            <h1>{data?.patient?.name}</h1>
            <div className="patient-stats">
              <div className="stat">
                <span className="material-symbols-rounded">event</span>
                {data?.patient?.appointments?.length || 0} appointments
              </div>
              <div className="stat">
                <span className="material-symbols-rounded">description</span>
                {data?.patient?.documents?.length || 0} documents
              </div>
              <div className="stat">
                <span className="material-symbols-rounded">chat</span>
                {data?.chat_history?.length || 0} messages
              </div>
            </div>
          </div>
        </div>

        <div className="detail-tabs">
          <button 
            className={`tab-btn ${activeTab === 'overview' ? 'active' : ''}`}
            onClick={() => setActiveTab('overview')}
          >
            <span className="material-symbols-rounded">info</span>
            Overview
          </button>
          <button 
            className={`tab-btn ${activeTab === 'chat' ? 'active' : ''}`}
            onClick={() => setActiveTab('chat')}
          >
            <span className="material-symbols-rounded">chat</span>
            Chat History
          </button>
          <button 
            className={`tab-btn ${activeTab === 'documents' ? 'active' : ''}`}
            onClick={() => setActiveTab('documents')}
          >
            <span className="material-symbols-rounded">folder</span>
            Documents
          </button>
        </div>

        <div className="tab-content">
          {activeTab === 'overview' && (
            <div className="overview-section">
              <h3>
                <span className="material-symbols-rounded">event</span>
                Appointments with {data?.doctor?.name}
              </h3>
              {data?.patient?.appointments?.length > 0 ? (
                <div className="appointments-list">
                  {data.patient.appointments.map((apt, idx) => (
                    <div key={idx} className="appointment-item">
                      <div className="appointment-date">
                        <span className="material-symbols-rounded">schedule</span>
                        {apt.time_slot}
                      </div>
                      <div className="appointment-problem">
                        <strong>Reported Problem:</strong>
                        <p>{apt.problem || 'No problem description available'}</p>
                        <button 
                          className={`generate-problem-btn ${apt.problem ? 'regenerate' : ''}`}
                          onClick={() => handleGenerateProblem(apt.slot_id)}
                          disabled={generatingProblem === apt.slot_id}
                        >
                          {generatingProblem === apt.slot_id ? (
                            <>
                              <span className="spinner-small"></span>
                              Generating...
                            </>
                          ) : (
                            <>
                              <span className="material-symbols-rounded">auto_awesome</span>
                              {apt.problem ? 'Regenerate Summary' : 'Generate Problem Summary'}
                            </>
                          )}
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="no-data-text">No appointments found</p>
              )}
            </div>
          )}

          {activeTab === 'chat' && (
            <div className="chat-section">
              <h3>
                <span className="material-symbols-rounded">chat</span>
                Patient Chat History
              </h3>
              {data?.chat_history?.length > 0 ? (
                <div className="chat-history">
                  {data.chat_history.map((msg, idx) => (
                    <div key={idx} className={`chat-message ${msg.role}`}>
                      <div className="message-header">
                        <span className="message-role">
                          {msg.role === 'user' ? 'Patient' : 'MedAssistant'}
                        </span>
                        <span className="message-time">{msg.timestamp}</span>
                      </div>
                      <div className="message-text">{msg.text}</div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="no-chat">
                  <span className="material-symbols-rounded">chat_bubble_outline</span>
                  <p>No chat history available for this patient</p>
                </div>
              )}
            </div>
          )}

          {activeTab === 'documents' && (
            <div className="documents-section">
              <h3>
                <span className="material-symbols-rounded">folder</span>
                Uploaded Documents
              </h3>
              {data?.patient?.documents?.length > 0 ? (
                <div className="documents-list">
                  {data.patient.documents.map((doc, idx) => (
                    <div key={idx} className="document-item">
                      <div className="document-icon">
                        <span className="material-symbols-rounded">description</span>
                      </div>
                      <div className="document-info">
                        <strong>{doc.filename}</strong>
                        <p>Uploaded: {doc.upload_date}</p>
                        {doc.description && <p className="doc-desc">{doc.description}</p>}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="no-docs">
                  <span className="material-symbols-rounded">folder_off</span>
                  <p>No documents uploaded by this patient</p>
                </div>
              )}
            </div>
          )}
        </div>
      </main>

      <style>{styles}</style>
    </div>
  );
};

const styles = `
  .doctor-container {
    min-height: 100vh;
    background: #f5f7fa;
  }

  .doctor-header {
    background: #0077B6;
    color: white;
    padding: 20px 30px;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .header-left {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .logo-icon {
    font-size: 32px;
  }

  .header-left h1 {
    margin: 0;
    font-size: 24px;
  }

  .header-right {
    display: flex;
    align-items: center;
    gap: 20px;
  }

  .doctor-name {
    font-size: 14px;
    opacity: 0.9;
  }

  .logout-btn {
    background: rgba(255, 255, 255, 0.2);
    border: none;
    color: white;
    padding: 8px 16px;
    border-radius: 8px;
    display: flex;
    align-items: center;
    gap: 6px;
    cursor: pointer;
    transition: all 0.2s;
  }

  .logout-btn:hover {
    background: rgba(255, 255, 255, 0.3);
  }

  .doctor-nav {
    background: white;
    padding: 0 30px;
    display: flex;
    gap: 8px;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
  }

  .nav-item {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 16px 20px;
    color: #666;
    text-decoration: none;
    border-bottom: 3px solid transparent;
    transition: all 0.2s;
  }

  .nav-item:hover {
    color: #0077B6;
  }

  .nav-item.active {
    color: #0077B6;
    border-bottom-color: #0077B6;
  }

  .doctor-main {
    padding: 30px;
    max-width: 1200px;
    margin: 0 auto;
  }

  .breadcrumb {
    margin-bottom: 20px;
  }

  .breadcrumb a {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    color: #0077B6;
    text-decoration: none;
    font-size: 14px;
  }

  .breadcrumb a:hover {
    text-decoration: underline;
  }

  .patient-header-card {
    background: white;
    border-radius: 16px;
    padding: 30px;
    display: flex;
    align-items: center;
    gap: 24px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
    margin-bottom: 24px;
  }

  .patient-avatar-large {
    width: 100px;
    height: 100px;
    background: #0077B6;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .patient-avatar-large .material-symbols-rounded {
    font-size: 50px;
    color: white;
  }

  .patient-header-info h1 {
    margin: 0 0 12px;
    color: #333;
  }

  .patient-stats {
    display: flex;
    gap: 24px;
  }

  .patient-stats .stat {
    display: flex;
    align-items: center;
    gap: 6px;
    color: #666;
    font-size: 14px;
  }

  .patient-stats .stat .material-symbols-rounded {
    font-size: 20px;
    color: #0077B6;
  }

  .detail-tabs {
    display: flex;
    gap: 12px;
    margin-bottom: 20px;
  }

  .tab-btn {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 12px 24px;
    background: white;
    border: 2px solid #e5e7eb;
    border-radius: 10px;
    font-size: 14px;
    font-weight: 500;
    color: #666;
    cursor: pointer;
    transition: all 0.2s;
  }

  .tab-btn:hover {
    border-color: #0077B6;
    color: #0077B6;
  }

  .tab-btn.active {
    background: #0077B6;
    border-color: #0077B6;
    color: white;
  }

  .tab-content {
    background: white;
    border-radius: 12px;
    padding: 24px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  }

  .tab-content h3 {
    display: flex;
    align-items: center;
    gap: 10px;
    margin: 0 0 20px;
    color: #333;
    padding-bottom: 16px;
    border-bottom: 1px solid #f0f0f0;
  }

  .appointments-list {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .appointment-item {
    background: #f9fafb;
    border-radius: 10px;
    padding: 16px;
    border-left: 4px solid #0077B6;
  }

  .appointment-date {
    display: flex;
    align-items: center;
    gap: 8px;
    color: #0077B6;
    font-weight: 500;
    margin-bottom: 12px;
  }

  .appointment-problem strong {
    color: #333;
    display: block;
    margin-bottom: 6px;
  }

  .appointment-problem p {
    margin: 0;
    color: #666;
    background: white;
    padding: 12px;
    border-radius: 8px;
    font-size: 14px;
    line-height: 1.5;
  }

  .generate-problem-btn {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    margin-top: 12px;
    padding: 8px 16px;
    background: #0077B6;
    color: white;
    border: none;
    border-radius: 8px;
    font-size: 13px;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s;
  }

  .generate-problem-btn:hover {
    background: #005f8a;
    box-shadow: 0 4px 12px rgba(0, 119, 182, 0.3);
  }

  .generate-problem-btn:disabled {
    opacity: 0.7;
    cursor: not-allowed;
    transform: none;
  }

  .generate-problem-btn.regenerate {
    background: #FFC107;
    color: #212529;
  }

  .generate-problem-btn.regenerate:hover {
    background: #e0a800;
    box-shadow: 0 4px 12px rgba(255, 193, 7, 0.4);
  }

  .generate-problem-btn .material-symbols-rounded {
    font-size: 18px;
  }

  .spinner-small {
    width: 16px;
    height: 16px;
    border: 2px solid rgba(255, 255, 255, 0.3);
    border-top-color: white;
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }

  @keyframes spin {
    to { transform: rotate(360deg); }
  }

  .chat-history {
    display: flex;
    flex-direction: column;
    gap: 16px;
    max-height: 600px;
    overflow-y: auto;
    padding-right: 10px;
  }

  .chat-message {
    padding: 16px;
    border-radius: 12px;
    max-width: 85%;
  }

  .chat-message.user {
    background: #e8f0fe;
    margin-left: auto;
    border-bottom-right-radius: 4px;
  }

  .chat-message.bot {
    background: #f1f3f5;
    margin-right: auto;
    border-bottom-left-radius: 4px;
  }

  .message-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 8px;
    font-size: 12px;
  }

  .message-role {
    font-weight: 600;
    color: #0077B6;
  }

  .chat-message.bot .message-role {
    color: #666;
  }

  .message-time {
    color: #999;
  }

  .message-text {
    color: #333;
    line-height: 1.5;
    font-size: 14px;
    white-space: pre-wrap;
  }

  .no-chat, .no-docs {
    text-align: center;
    padding: 40px;
    color: #888;
  }

  .no-chat .material-symbols-rounded,
  .no-docs .material-symbols-rounded {
    font-size: 48px;
    color: #ddd;
    margin-bottom: 12px;
  }

  .documents-list {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .document-item {
    display: flex;
    align-items: flex-start;
    gap: 16px;
    padding: 16px;
    background: #f9fafb;
    border-radius: 10px;
  }

  .document-icon {
    width: 48px;
    height: 48px;
    background: #0077B6;
    border-radius: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .document-icon .material-symbols-rounded {
    color: white;
    font-size: 24px;
  }

  .document-info strong {
    color: #333;
    display: block;
    margin-bottom: 4px;
  }

  .document-info p {
    margin: 0;
    color: #888;
    font-size: 13px;
  }

  .doc-desc {
    margin-top: 8px !important;
    color: #666 !important;
  }

  .no-data-text {
    color: #888;
    font-style: italic;
  }

  .error-page {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: calc(100vh - 80px);
    color: #666;
  }

  .error-page .material-symbols-rounded {
    font-size: 64px;
    color: #dc2626;
  }

  .error-page h2 {
    margin: 16px 0;
  }

  .back-btn {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 12px 24px;
    background: #0077B6;
    color: white;
    border-radius: 10px;
    text-decoration: none;
    margin-top: 16px;
  }

  .loading {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 10px;
    height: 100vh;
    font-size: 18px;
    color: #666;
  }

  .spinner {
    width: 24px;
    height: 24px;
    border: 3px solid #e5e7eb;
    border-top-color: #0077B6;
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }

  @keyframes spin {
    to { transform: rotate(360deg); }
  }
`;

export default PatientDetail;
