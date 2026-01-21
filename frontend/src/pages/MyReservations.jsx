import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

const API_BASE = `http://localhost:${import.meta.env.VITE_API_PORT || 8000}`;

const MyReservations = () => {
  const { user, logout } = useAuth();
  const [reservations, setReservations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [cancellingId, setCancellingId] = useState(null);
  const [toast, setToast] = useState({ show: false, message: '', type: 'success' });

  // Fetch reservations after the component mounts

  useEffect(() => {
    fetchReservations();
  }, []);

  // Auto-hide toast after 4 seconds
  useEffect(() => {
    if (toast.show) {
      const timer = setTimeout(() => {
        setToast({ ...toast, show: false });
      }, 4000);
      return () => clearTimeout(timer);
    }
  }, [toast.show]);

  const fetchReservations = async () => {
    try {
      // credentials: 'include' sends the session cookie automatically
      const response = await fetch(`${API_BASE}/api/my-reservations`, {
        credentials: 'include'
      });
      if (!response.ok) throw new Error('Failed to fetch reservations');
      const data = await response.json();
      setReservations(data.reservations || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleCancel = async (slotId, doctorName, timeSlot) => {
    if (!window.confirm('Are you sure you want to cancel this appointment?')) return;
    
    setCancellingId(slotId);
    try {
      const response = await fetch(`${API_BASE}/api/cancel-slot/${slotId}`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({})
      });
      
      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.error || 'Failed to cancel');
      }
      
      // Remove from list
      setReservations(prev => prev.filter(r => r.slot_id !== slotId));
      
      setToast({
        show: true,
        message: `Appointment with ${doctorName} for ${timeSlot} cancelled successfully`,
        type: 'success'
      });
    } catch (err) {
      setToast({
        show: true,
        message: `Error: ${err.message}`,
        type: 'error'
      });
    } finally {
      setCancellingId(null);
    }
  };

  if (loading) {
    return (
      <div className="page-container">
        <div className="loading">Loading your reservations...</div>
      </div>
    );
  }

  return (
    <div className="page-container">
      {/* Toast Notification Overlay */}
      {toast.show && (
        <div className={`toast-overlay ${toast.type}`}>
          <div className="toast-content">
            <span>{toast.message}</span>
            <button className="toast-close" onClick={() => setToast({ ...toast, show: false })}>×</button>
          </div>
        </div>
      )}

      <div className="page-header">
        <h1>My Reservations</h1>
      </div>

      {error && <div className="error-message">{error}</div>}

      {reservations.length === 0 ? (
        <div className="empty-state">
          <p>You don't have any appointments scheduled.</p>
          <Link to="/doctors" className="btn-primary">Book an Appointment</Link>
        </div>
      ) : (
        <div className="reservations-grid">
          {reservations.map((res) => (
            <div key={res.slot_id} className="reservation-card">
              <div className="card-header">
                <span className="specialization">{res.specialization}</span>
              </div>
              <div className="card-body">
                <h3>{res.doctor}</h3>
                <p className="time-slot"> {res.time_slot}</p>
                <p className="slot-id">Slot ID: {res.slot_id}</p>
              </div>
              <div className="card-actions">
                <button 
                  className="btn-cancel"
                  onClick={() => handleCancel(res.slot_id, res.doctor, res.time_slot)}
                  disabled={cancellingId === res.slot_id}
                >
                  {cancellingId === res.slot_id ? 'Cancelling...' : ' Cancel'}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      <style>{`
        .page-container {
          width: 100%;
          min-height: calc(100vh - 60px);
          padding: 30px 40px;
          font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
          background: #F8F9FA;
        }
        
        /* Toast Overlay - Fixed position */
        .toast-overlay {
          position: fixed;
          top: 30px;
          left: 50%;
          transform: translateX(-50%);
          z-index: 9999;
          animation: slideDown 0.3s ease-out;
        }
        .toast-content {
          display: flex;
          align-items: center;
          gap: 15px;
          padding: 18px 28px;
          border-radius: 12px;
          box-shadow: 0 8px 30px rgba(0,0,0,0.25);
          font-size: 1.1em;
          font-weight: 500;
          min-width: 350px;
          max-width: 600px;
        }
        .toast-overlay.success .toast-content {
          background: #28A745;
          color: white;
        }
        .toast-overlay.error .toast-content {
          background: #DC3545;
          color: white;
        }
        .toast-close {
          background: rgba(255,255,255,0.2);
          border: none;
          color: white;
          font-size: 1.5em;
          cursor: pointer;
          padding: 2px 10px;
          border-radius: 50%;
          line-height: 1;
          margin-left: auto;
        }
        .toast-close:hover {
          background: rgba(255,255,255,0.3);
        }
        @keyframes slideDown {
          from {
            opacity: 0;
            transform: translateX(-50%) translateY(-20px);
          }
          to {
            opacity: 1;
            transform: translateX(-50%) translateY(0);
          }
        }
        
        .page-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 30px;
          padding-bottom: 20px;
          border-bottom: 2px solid #e0e0e0;
        }
        .page-header h1 {
          color: #2c3e50;
          margin: 0;
          font-size: 2em;
        }
        .loading {
          text-align: center;
          padding: 50px;
          font-size: 1.3em;
          color: #666;
        }
        .error-message {
          background: #fee;
          color: #c00;
          padding: 15px;
          border-radius: 8px;
          margin-bottom: 20px;
        }
        .empty-state {
          text-align: center;
          padding: 60px;
          background: #f9f9f9;
          border-radius: 16px;
        }
        .empty-state p {
          color: #666;
          margin-bottom: 25px;
          font-size: 1.2em;
        }
        .btn-primary {
          background: #0077B6;
          color: white;
          padding: 14px 28px;
          border: none;
          border-radius: 10px;
          text-decoration: none;
          font-weight: 600;
          font-size: 1.1em;
          cursor: pointer;
        }
        .btn-primary:hover {
          opacity: 0.9;
        }
        .reservations-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
          gap: 20px;
        }
        .reservation-card {
          background: white;
          border-radius: 14px;
          box-shadow: 0 4px 16px rgba(0,0,0,0.1);
          overflow: hidden;
          transition: transform 0.2s;
          min-height: 200px;
          display: flex;
          flex-direction: column;
        }
        .reservation-card:hover {
          transform: translateY(-5px);
        }
        .card-header {
          background: #0077B6;
          color: white;
          padding: 18px 20px;
        }
        .specialization {
          font-weight: 600;
          font-size: 1em;
          text-transform: uppercase;
        }
        .card-body {
          padding: 25px;
          flex: 1;
        }
        .card-body h3 {
          margin: 0 0 12px 0;
          color: #2c3e50;
          font-size: 1.3em;
        }
        .time-slot {
          color: #555;
          margin: 8px 0;
          font-size: 1.1em;
        }
        .slot-id {
          color: #999;
          font-size: 0.9em;
        }
        .card-actions {
          padding: 18px 25px;
          border-top: 1px solid #eee;
        }
        .btn-cancel {
          background: #e74c3c;
          color: white;
          border: none;
          padding: 12px 24px;
          border-radius: 8px;
          cursor: pointer;
          width: 100%;
          font-weight: 600;
          font-size: 1em;
          min-height: 48px;
        }
        .btn-cancel:hover:not(:disabled) {
          background: #c0392b;
        }
        .btn-cancel:disabled {
          opacity: 0.6;
          cursor: not-allowed;
        }
        
        @media (max-width: 500px) {
          .reservations-grid {
            grid-template-columns: 1fr;
          }
        }
      `}</style>
    </div>
  );
};

export default MyReservations;
