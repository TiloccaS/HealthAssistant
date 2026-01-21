import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

const API_BASE = `http://localhost:${import.meta.env.VITE_API_PORT || 8000}`;

const DoctorDashboard = () => {
  const [dashboard, setDashboard] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  const { user, doctorInfo, logout, isDoctor } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (!isDoctor) {
      navigate('/login');
      return;
    }
    fetchDashboard();
  }, [isDoctor, navigate]);

  const fetchDashboard = async () => {
    try {
      // credentials: 'include' sends the session cookie automatically
      const response = await fetch(`${API_BASE}/api/doctor/dashboard`, {
        credentials: 'include'
      });
      
      if (!response.ok) {
        if (response.status === 401) {
          navigate('/login');
          return;
        }
        throw new Error('Failed to fetch dashboard');
      }
      
      const data = await response.json();
      setDashboard(data);
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
          Loading dashboard...
        </div>
        <style>{styles}</style>
      </div>
    );
  }

  if (error) {
    return (
      <div className="doctor-container">
        <div className="error-message">
          <span className="material-symbols-rounded">error</span>
          {error}
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
            {dashboard?.doctor?.name} - {dashboard?.doctor?.specialization}
          </span>
          <button onClick={handleLogout} className="logout-btn">
            <span className="material-symbols-rounded">logout</span>
            Logout
          </button>
        </div>
      </header>

      <nav className="doctor-nav">
        <Link to="/doctor/dashboard" className="nav-item active">
          <span className="material-symbols-rounded">dashboard</span>
          Dashboard
        </Link>
        <Link to="/doctor/patients" className="nav-item">
          <span className="material-symbols-rounded">group</span>
          My Patients
        </Link>
        <Link to="/doctor/appointments" className="nav-item">
          <span className="material-symbols-rounded">calendar_month</span>
          Appointments
        </Link>
      </nav>

      <main className="doctor-main">
        <div className="stats-grid">
          <div className="stat-card patients">
            <div className="stat-icon">
              <span className="material-symbols-rounded">group</span>
            </div>
            <div className="stat-info">
              <h3>{dashboard?.stats?.total_patients || 0}</h3>
              <p>Total Patients</p>
            </div>
          </div>
          
          <div className="stat-card booked">
            <div className="stat-icon">
              <span className="material-symbols-rounded">event_available</span>
            </div>
            <div className="stat-info">
              <h3>{dashboard?.stats?.total_booked || 0}</h3>
              <p>Booked Appointments</p>
            </div>
          </div>
          
          <div className="stat-card available">
            <div className="stat-icon">
              <span className="material-symbols-rounded">event_note</span>
            </div>
            <div className="stat-info">
              <h3>{dashboard?.stats?.total_available || 0}</h3>
              <p>Available Slots</p>
            </div>
          </div>
        </div>

        <section className="upcoming-section">
          <h2>
            <span className="material-symbols-rounded">schedule</span>
            Upcoming Appointments
          </h2>
          
          {dashboard?.upcoming_appointments?.length > 0 ? (
            <div className="appointments-list">
              {dashboard.upcoming_appointments.map((apt) => (
                <div key={apt.slot_id} className="appointment-card">
                  <div className="appointment-time">
                    <span className="material-symbols-rounded">schedule</span>
                    {apt.time_slot}
                  </div>
                  <div className="appointment-patient">
                    <h4>{apt.patient}</h4>
                    <p>{apt.problem || 'No problem description'}</p>
                  </div>
                  <Link 
                    to={`/doctor/patient/${apt.patient}`} 
                    className="view-btn"
                  >
                    <span className="material-symbols-rounded">visibility</span>
                    View Details
                  </Link>
                </div>
              ))}
            </div>
          ) : (
            <div className="no-appointments">
              <span className="material-symbols-rounded">event_busy</span>
              <p>No upcoming appointments</p>
            </div>
          )}
        </section>
      </main>

      <style>{styles}</style>
    </div>
  );
};

const styles = `
  .doctor-container {
    min-height: 100vh;
    background: #F8F9FA;
  }

  .doctor-header {
    background: #0077B6;
    color: white;
    padding: 16px 24px;
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

  .stats-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
    gap: 20px;
    margin-bottom: 30px;
  }

  .stat-card {
    background: white;
    border-radius: 12px;
    padding: 24px;
    display: flex;
    align-items: center;
    gap: 20px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  }

  .stat-icon {
    width: 60px;
    height: 60px;
    border-radius: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .stat-icon .material-symbols-rounded {
    font-size: 28px;
    color: white;
  }

  .stat-card.patients .stat-icon {
    background: #0077B6;
  }

  .stat-card.booked .stat-icon {
    background: #28A745;
  }

  .stat-card.available .stat-icon {
    background: #FFC107;
  }

  .stat-info h3 {
    font-size: 32px;
    margin: 0;
    color: #333;
  }

  .stat-info p {
    margin: 4px 0 0;
    color: #888;
    font-size: 14px;
  }

  .upcoming-section {
    background: white;
    border-radius: 12px;
    padding: 24px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  }

  .upcoming-section h2 {
    display: flex;
    align-items: center;
    gap: 10px;
    margin: 0 0 20px;
    color: #333;
    font-size: 20px;
  }

  .appointments-list {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .appointment-card {
    display: flex;
    align-items: center;
    gap: 20px;
    padding: 16px;
    background: #F8F9FA;
    border-radius: 8px;
    border-left: 4px solid #0077B6;
  }

  .appointment-time {
    display: flex;
    align-items: center;
    gap: 6px;
    color: #0077B6;
    font-weight: 500;
    min-width: 180px;
  }

  .appointment-patient {
    flex: 1;
  }

  .appointment-patient h4 {
    margin: 0;
    color: #333;
  }

  .appointment-patient p {
    margin: 4px 0 0;
    color: #888;
    font-size: 13px;
  }

  .view-btn {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 8px 16px;
    background: #0077B6;
    color: white;
    border-radius: 6px;
    text-decoration: none;
    font-size: 14px;
    transition: background 0.2s;
  }

  .view-btn:hover {
    background: #005f92;
  }

  .no-appointments {
    text-align: center;
    padding: 40px;
    color: #888;
  }

  .no-appointments .material-symbols-rounded {
    font-size: 48px;
    color: #ddd;
  }

  .loading, .error-message {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 10px;
    height: 100vh;
    font-size: 18px;
    color: #666;
  }

  .error-message {
    color: #dc2626;
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

export default DoctorDashboard;
