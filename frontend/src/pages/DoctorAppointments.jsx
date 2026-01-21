import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

const API_BASE = `http://localhost:${import.meta.env.VITE_API_PORT || 8000}`;

const DoctorAppointments = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('booked');
  
  const { logout, isDoctor } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (!isDoctor) {
      navigate('/login');
      return;
    }
    fetchAppointments();
  }, [isDoctor, navigate]);

  const fetchAppointments = async () => {
    try {
      // credentials: 'include' sends the session cookie automatically
      const response = await fetch(`${API_BASE}/api/doctor/appointments`, {
        credentials: 'include'
      });
      
      if (!response.ok) {
        if (response.status === 401) {
          navigate('/login');
          return;
        }
        throw new Error('Failed to fetch appointments');
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

  if (loading) {
    return (
      <div className="doctor-container">
        <div className="loading">
          <span className="spinner"></span>
          Loading appointments...
        </div>
        <style>{styles}</style>
      </div>
    );
  }

  const appointments = activeTab === 'booked' 
    ? data?.appointments?.booked || []
    : data?.appointments?.available || [];

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
        <Link to="/doctor/patients" className="nav-item">
          <span className="material-symbols-rounded">group</span>
          My Patients
        </Link>
        <Link to="/doctor/appointments" className="nav-item active">
          <span className="material-symbols-rounded">calendar_month</span>
          Appointments
        </Link>
      </nav>

      <main className="doctor-main">
        <div className="page-header">
          <h2>
            <span className="material-symbols-rounded">calendar_month</span>
            My Appointments
          </h2>
        </div>

        {error && (
          <div className="error-banner">
            <span className="material-symbols-rounded">error</span>
            {error}
          </div>
        )}

        <div className="tabs-container">
          <button 
            className={`tab-btn ${activeTab === 'booked' ? 'active' : ''}`}
            onClick={() => setActiveTab('booked')}
          >
            <span className="material-symbols-rounded">event_available</span>
            Booked ({data?.appointments?.total_booked || 0})
          </button>
          <button 
            className={`tab-btn ${activeTab === 'available' ? 'active' : ''}`}
            onClick={() => setActiveTab('available')}
          >
            <span className="material-symbols-rounded">event_note</span>
            Available ({data?.appointments?.total_available || 0})
          </button>
        </div>

        <div className="appointments-content">
          {appointments.length > 0 ? (
            <div className="appointments-list">
              {appointments.map((apt) => (
                <div key={apt.slot_id} className={`appointment-card ${apt.status}`}>
                  <div className="appointment-time">
                    <span className="material-symbols-rounded">schedule</span>
                    <div>
                      <strong>{apt.time_slot}</strong>
                      <span className={`status-badge ${apt.status}`}>
                        {apt.status === 'booked' ? 'Booked' : 'Available'}
                      </span>
                    </div>
                  </div>
                  
                  {apt.patient && (
                    <div className="appointment-details">
                      <div className="patient-info">
                        <span className="material-symbols-rounded">person</span>
                        <div>
                          <strong>{apt.patient}</strong>
                          <p>{apt.patient_problem || 'No problem description'}</p>
                        </div>
                      </div>
                      <Link 
                        to={`/doctor/patient/${apt.patient}`} 
                        className="view-btn"
                      >
                        <span className="material-symbols-rounded">visibility</span>
                        View Patient
                      </Link>
                    </div>
                  )}
                  
                  {!apt.patient && (
                    <div className="appointment-details empty">
                      <span className="material-symbols-rounded">event_available</span>
                      <p>This slot is available for booking</p>
                    </div>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <div className="no-data">
              <span className="material-symbols-rounded">
                {activeTab === 'booked' ? 'event_busy' : 'event_available'}
              </span>
              <h3>No {activeTab} appointments</h3>
              <p>
                {activeTab === 'booked' 
                  ? 'You have no booked appointments yet' 
                  : 'All your slots are booked'}
              </p>
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

  .page-header {
    margin-bottom: 24px;
  }

  .page-header h2 {
    display: flex;
    align-items: center;
    gap: 10px;
    margin: 0;
    color: #333;
  }

  .error-banner {
    background: #fee2e2;
    border: 1px solid #ef4444;
    color: #dc2626;
    padding: 12px 16px;
    border-radius: 8px;
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 20px;
  }

  .tabs-container {
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

  .appointments-content {
    background: white;
    border-radius: 12px;
    padding: 24px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  }

  .appointments-list {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .appointment-card {
    border: 1px solid #e5e7eb;
    border-radius: 12px;
    padding: 20px;
    transition: all 0.2s;
  }

  .appointment-card.booked {
    border-left: 4px solid #22c55e;
  }

  .appointment-card.available {
    border-left: 4px solid #f59e0b;
  }

  .appointment-card:hover {
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
  }

  .appointment-time {
    display: flex;
    align-items: flex-start;
    gap: 12px;
    margin-bottom: 16px;
  }

  .appointment-time .material-symbols-rounded {
    color: #0077B6;
    font-size: 24px;
  }

  .appointment-time strong {
    display: block;
    color: #333;
    margin-bottom: 4px;
  }

  .status-badge {
    display: inline-block;
    padding: 4px 10px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 500;
  }

  .status-badge.booked {
    background: #dcfce7;
    color: #16a34a;
  }

  .status-badge.available {
    background: #fef3c7;
    color: #d97706;
  }

  .appointment-details {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding-top: 16px;
    border-top: 1px solid #f0f0f0;
  }

  .appointment-details.empty {
    justify-content: flex-start;
    gap: 10px;
    color: #888;
  }

  .patient-info {
    display: flex;
    align-items: flex-start;
    gap: 12px;
  }

  .patient-info .material-symbols-rounded {
    width: 40px;
    height: 40px;
    background: #f0f0f0;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #666;
  }

  .patient-info strong {
    display: block;
    color: #333;
  }

  .patient-info p {
    margin: 4px 0 0;
    color: #888;
    font-size: 13px;
  }

  .view-btn {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 10px 20px;
    background: #0077B6;
    color: white;
    border-radius: 8px;
    text-decoration: none;
    font-size: 14px;
    transition: all 0.2s;
  }

  .view-btn:hover {
    background: #5568d3;
  }

  .no-data {
    text-align: center;
    padding: 60px 20px;
  }

  .no-data .material-symbols-rounded {
    font-size: 64px;
    color: #ddd;
  }

  .no-data h3 {
    color: #666;
    margin: 16px 0 8px;
  }

  .no-data p {
    color: #999;
    margin: 0;
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

export default DoctorAppointments;
