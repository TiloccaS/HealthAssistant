import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

const API_BASE = `http://localhost:${import.meta.env.VITE_API_PORT || 8000}`;

const Doctors = () => {
  const { user } = useAuth();
  const [doctors, setDoctors] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [bookingSlot, setBookingSlot] = useState(null);
  const [toast, setToast] = useState({ show: false, message: '', type: 'success' });

  useEffect(() => {
    fetchDoctors();
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

  const fetchDoctors = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/doctors`);
      if (!response.ok) throw new Error('Failed to fetch doctors');
      const data = await response.json();
      setDoctors(data.doctors || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleBook = async (slotId, doctorName, timeSlot) => {
    setBookingSlot(slotId);
    
    try {
      // credentials: 'include' sends the session cookie automatically
      const response = await fetch(`${API_BASE}/api/book-slot/${slotId}`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({})
      });
      
      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.error || 'Failed to book');
      }
      
      setToast({
        show: true,
        message: `Booked appointment with ${doctorName} for ${timeSlot}`,
        type: 'success'
      });
      
      // Refresh doctors list
      fetchDoctors();
    } catch (err) {
      setToast({
        show: true,
        message: `Error: ${err.message}`,
        type: 'error'
      });
    } finally {
      setBookingSlot(null);
    }
  };

  if (loading) {
    return (
      <div className="page-container">
        <div className="loading">Loading doctors...</div>
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
        <h1>Our Doctors</h1>
      </div>

      {error && <div className="error-message">{error}</div>}

      <div className="doctors-grid">
        {doctors.map((doctor) => (
          <div key={doctor.name} className="doctor-card">
            <div className="doctor-header">
              <div className="doctor-info">
                <h3>{doctor.name}</h3>
                <span className="specialization">{doctor.specialization}</span>
              </div>
            </div>
            
            <div className="slots-section">
              <h4>Available Slots</h4>
              {doctor.slots.length === 0 ? (
                <p className="no-slots">No available slots</p>
              ) : (
                <div className="slots-list">
                  {doctor.slots.map((slot) => (
                    <div key={slot.id} className="slot-item">
                      <span className="slot-time">{slot.time_slot}</span>
                      <button
                        className="btn-book"
                        onClick={() => handleBook(slot.id, doctor.name, slot.time_slot)}
                        disabled={bookingSlot === slot.id}
                      >
                        {bookingSlot === slot.id ? 'Booking...' : 'Book'}
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

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
        .doctors-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
          gap: 24px;
        }
        .doctor-card {
          background: white;
          border-radius: 16px;
          box-shadow: 0 4px 20px rgba(0,0,0,0.1);
          overflow: hidden;
          display: flex;
          flex-direction: column;
          min-height: 380px;
        }
        .doctor-header {
          background: #0077B6;
          color: white;
          padding: 30px;
          display: flex;
          align-items: center;
          gap: 20px;
          flex-shrink: 0;
        }
        .doctor-avatar {
          font-size: 3em;
          background: rgba(255,255,255,0.2);
          width: 80px;
          height: 80px;
          display: flex;
          align-items: center;
          justify-content: center;
          border-radius: 50%;
          flex-shrink: 0;
        }
        .doctor-info h3 {
          margin: 0;
          font-size: 1.5em;
        }
        .specialization {
          opacity: 0.9;
          font-size: 1.1em;
        }
        .slots-section {
          padding: 25px;
          flex: 1;
          display: flex;
          flex-direction: column;
        }
        .slots-section h4 {
          margin: 0 0 18px 0;
          color: #2c3e50;
          font-size: 1.2em;
          flex-shrink: 0;
        }
        .no-slots {
          color: #999;
          font-style: italic;
          font-size: 1.1em;
        }
        .slots-list {
          display: flex;
          flex-direction: column;
          gap: 12px;
          max-height: 280px;
          overflow-y: auto;
          flex: 1;
        }
        .slot-item {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 14px 18px;
          background: #f8f9fa;
          border-radius: 10px;
          min-height: 54px;
          box-sizing: border-box;
        }
        .slot-time {
          color: #555;
          flex: 1;
          font-size: 1.05em;
        }
        .btn-book {
          background: #27ae60;
          color: white;
          border: none;
          padding: 10px 24px;
          border-radius: 8px;
          cursor: pointer;
          font-weight: 600;
          font-size: 1em;
          transition: background 0.2s, opacity 0.2s;
          min-width: 100px;
          height: 42px;
          display: flex;
          align-items: center;
          justify-content: center;
          flex-shrink: 0;
        }
        .btn-book:hover:not(:disabled) {
          background: #219a52;
        }
        .btn-book:disabled {
          opacity: 0.6;
          cursor: not-allowed;
        }
        
        @media (max-width: 500px) {
          .doctors-grid {
            grid-template-columns: 1fr;
          }
        }
      `}</style>
    </div>
  );
};

export default Doctors;
