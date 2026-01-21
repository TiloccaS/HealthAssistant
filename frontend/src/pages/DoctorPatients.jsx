import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

const API_BASE = `http://localhost:${import.meta.env.VITE_API_PORT || 8000}`;

const DoctorPatients = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  
  const { logout, isDoctor } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (!isDoctor) {
      navigate('/login');
      return;
    }
    fetchPatients();
  }, [isDoctor, navigate]);

  const fetchPatients = async () => {
    try {
      // credentials: 'include' sends the session cookie automatically
      const response = await fetch(`${API_BASE}/api/doctor/patients`, {
        credentials: 'include'
      });
      
      if (!response.ok) {
        if (response.status === 401) {
          navigate('/login');
          return;
        }
        throw new Error('Failed to fetch patients');
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

  const filteredPatients = data?.patients?.filter(patient =>
    patient.name.toLowerCase().includes(searchTerm.toLowerCase())
  ) || [];

  if (loading) {
    return (
      <div className="doctor-container">
        <div className="loading">
          <span className="spinner"></span>
          Loading patients...
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
        <div className="page-header">
          <h2>
            <span className="material-symbols-rounded">group</span>
            My Patients ({data?.total_patients || 0})
          </h2>
          <div className="search-box">
            <span className="material-symbols-rounded">search</span>
            <input
              type="text"
              placeholder="Search patients..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>
        </div>

        {error && (
          <div className="error-banner">
            <span className="material-symbols-rounded">error</span>
            {error}
          </div>
        )}

        {filteredPatients.length > 0 ? (
          <div className="patients-grid">
            {filteredPatients.map((patient) => (
              <div key={patient.name} className="patient-card">
                <div className="patient-avatar">
                  <span className="material-symbols-rounded">person</span>
                </div>
                <div className="patient-info">
                  <h3>{patient.name}</h3>
                  <p className="appointments-count">
                    <span className="material-symbols-rounded">event</span>
                    {patient.appointments.length} appointment{patient.appointments.length !== 1 ? 's' : ''}
                  </p>
                  {patient.appointments[0]?.problem && (
                    <p className="latest-problem">
                      <strong>Latest issue:</strong> {patient.appointments[0].problem}
                    </p>
                  )}
                </div>
                <div className="patient-actions">
                  <Link to={`/doctor/patient/${patient.name}`} className="view-btn">
                    <span className="material-symbols-rounded">visibility</span>
                    View Details
                  </Link>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="no-data">
            <span className="material-symbols-rounded">person_off</span>
            <h3>No patients found</h3>
            <p>{searchTerm ? 'Try a different search term' : 'You have no patients with appointments yet'}</p>
          </div>
        )}
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
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 24px;
  }

  .page-header h2 {
    display: flex;
    align-items: center;
    gap: 10px;
    margin: 0;
    color: #333;
  }

  .search-box {
    display: flex;
    align-items: center;
    gap: 8px;
    background: white;
    padding: 10px 16px;
    border-radius: 10px;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
  }

  .search-box .material-symbols-rounded {
    color: #888;
  }

  .search-box input {
    border: none;
    outline: none;
    font-size: 14px;
    width: 200px;
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

  .patients-grid {
    display: grid;
    gap: 16px;
  }

  .patient-card {
    background: white;
    border-radius: 12px;
    padding: 20px;
    display: flex;
    align-items: center;
    gap: 20px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
    transition: all 0.2s;
  }

  .patient-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.12);
  }

  .patient-avatar {
    width: 60px;
    height: 60px;
    background: #0077B6;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .patient-avatar .material-symbols-rounded {
    font-size: 30px;
    color: white;
  }

  .patient-info {
    flex: 1;
  }

  .patient-info h3 {
    margin: 0 0 6px;
    color: #333;
  }

  .appointments-count {
    display: flex;
    align-items: center;
    gap: 4px;
    color: #0077B6;
    font-size: 14px;
    margin: 0 0 8px;
  }

  .appointments-count .material-symbols-rounded {
    font-size: 18px;
  }

  .latest-problem {
    color: #666;
    font-size: 13px;
    margin: 0;
    background: #f5f5f5;
    padding: 8px 12px;
    border-radius: 6px;
  }

  .patient-actions {
    display: flex;
    gap: 10px;
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
    background: white;
    border-radius: 12px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
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

export default DoctorPatients;
