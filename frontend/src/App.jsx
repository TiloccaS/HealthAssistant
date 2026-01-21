import React, { useState, useEffect, useRef, useCallback } from "react";
import { BrowserRouter, Routes, Route, Navigate, Link } from "react-router-dom";
import { AuthProvider, useAuth } from "./context/AuthContext";
import ChatbotIcon from "./Components/ChatbotIcon";
import ChatMessage from "./Components/ChatMessage";
import ChatForm from "./Components/ChatForm";
import MyReservations from "./pages/MyReservations";
import Doctors from "./pages/Doctors";
import Login from "./pages/Login";
import Register from "./pages/Register";
import DoctorDashboard from "./pages/DoctorDashboard";
import DoctorPatients from "./pages/DoctorPatients";
import DoctorAppointments from "./pages/DoctorAppointments";
import PatientDetail from "./pages/PatientDetail";

const API_BASE = `http://localhost:${import.meta.env.VITE_API_PORT || 8000}`;

// Protected Route component
const ProtectedRoute = ({ children, allowedRoles = [] }) => {
  const { isAuthenticated, user, loading } = useAuth();
  
  if (loading) {
    return (
      <div className="loading-screen">
        <div className="spinner"></div>
        <p>Loading...</p>
      </div>
    );
  }
  
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }
  
  if (allowedRoles.length > 0 && !allowedRoles.includes(user?.role)) {
    return <Navigate to="/" replace />;
  }
  
  return children;
};

// Navigation Header for authenticated users
const NavHeader = () => {
  const { user, logout, isDoctor } = useAuth();
  
  const handleLogout = async () => {
    await logout();
  };
  
  if (!user) return null;
  
  return (
    <nav className="main-nav">
      <div className="nav-brand">
        <span className="material-symbols-rounded">healing</span>
        <span>MedAssistant</span>
      </div>
      <div className="nav-links">
        {!isDoctor && (
          <>
            <Link to="/" className="nav-link">
              <span className="material-symbols-rounded">chat</span>
              Chat
            </Link>
            <Link to="/doctors" className="nav-link">
              <span className="material-symbols-rounded">medical_services</span>
              Doctors
            </Link>
            <Link to="/my-reservations" className="nav-link">
              <span className="material-symbols-rounded">calendar_month</span>
              My Reservations
            </Link>
          </>
        )}
        {isDoctor && (
          <Link to="/doctor/dashboard" className="nav-link">
            <span className="material-symbols-rounded">dashboard</span>
            Doctor Portal
          </Link>
        )}
      </div>
      <div className="nav-user">
        <span className="user-name">
          <span className="material-symbols-rounded">person</span>
          {user.full_name}
        </span>
        <button onClick={handleLogout} className="logout-btn">
          <span className="material-symbols-rounded">logout</span>
          Logout
        </button>
      </div>
    </nav>
  );
};

// =============================================================================
// CHAT APPLICATION COMPONENT
// =============================================================================
// This component handles the main chat interface and WebSocket connection.

const ChatApp = () => {
  const { user, isAuthenticated } = useAuth();
  const [chatHistory, setChatHistory] = useState([]);
  const [isConnected, setIsConnected] = useState(false);
  const [isWaitingForResponse, setIsWaitingForResponse] = useState(false);
  const [isLoadingHistory, setIsLoadingHistory] = useState(true);
  const ws = useRef(null);  // Reference to WebSocket connection
  const chatBodyRef = useRef(null);  // Reference to chat container for scrolling

  // Scroll to bottom of chat when new messages arrive
  const scrollToBottom = () => {
    if (chatBodyRef.current) {
      chatBodyRef.current.scrollTop = chatBodyRef.current.scrollHeight;
    }
  };

  // Scroll whenever chat history changes
  useEffect(() => {
    scrollToBottom();
  }, [chatHistory]);

  /**
   * Load chat history from the backend when the component mounts.
   * The backend returns the chat history for the currently logged-in user.
   */
  useEffect(() => {
    const loadChatHistory = async () => {
      try {
        const response = await fetch(`${API_BASE}/api/chat-history`, {
          credentials: 'include'  // Send session cookie
        });
        
        if (response.ok) {
          const data = await response.json();
          /*
          without the control below if the user change account the chat history
          of the previous user would be shown to the new user
          */

          // Check if user changed - clear cached history if different
          const cachedUser = localStorage.getItem('medassist_current_user');
          if (cachedUser && cachedUser !== data.user_name) {
            localStorage.removeItem('medassist_chat_history');
          }
          localStorage.setItem('medassist_current_user', data.user_name);
          
          if (data.messages && data.messages.length > 0) {
            //if there are messages it load them anf format them
            const formattedMessages = data.messages.map(msg => ({
              role: msg.role === 'user' ? 'user' : 'model',
              text: msg.text
            }));
            setChatHistory(formattedMessages);
            localStorage.setItem('medassist_chat_history', JSON.stringify(formattedMessages));
          } else {
            setChatHistory([]);
            localStorage.removeItem('medassist_chat_history');
          }
        }
      } catch (error) {
        console.error('Failed to load chat history:', error);
        setChatHistory([]);
      } finally {
        setIsLoadingHistory(false);
      }
    };

    loadChatHistory();
  }, []);

  // Save chat history to localStorage as backup
  useEffect(() => {
    if (chatHistory.length > 0 && !isLoadingHistory) {
      localStorage.setItem('medassist_chat_history', JSON.stringify(chatHistory));
    }
  }, [chatHistory, isLoadingHistory]);

  /**
   * Connect to WebSocket for real-time chat.
   * 
   * We pass the username as a query parameter so the backend knows 
   * who is chatting (WebSocket can't access session cookies directly).
   */
  const connectWebSocket = useCallback(() => {
    // Build WebSocket URL with username for identification
    const username = user?.full_name || 'Guest';
    const encodedUsername = encodeURIComponent(username);
    const wsUrl = `ws://localhost:${import.meta.env.VITE_API_PORT || 8000}/ws?username=${encodedUsername}`;
    
    ws.current = new WebSocket(wsUrl);

    ws.current.onopen = () => {
      console.log("WebSocket Connected");
      setIsConnected(true);
    };

    ws.current.onclose = () => {
      console.log("WebSocket Disconnected");
      setIsConnected(false);
      setChatHistory((prev) => [
        ...prev,
        { role: "model", text: "Connection lost. Please refresh." },
      ]);
    };

    ws.current.onerror = (error) => {
      console.error("WebSocket Error:", error);
      setChatHistory((prev) => [
        ...prev,
        { role: "model", text: "Connection error. Please refresh." },
      ]);
    };

    // Handle incoming messages from the server
    ws.current.onmessage = (event) => {
      const message = event.data;
      console.log("Message from server:", message);
      setIsWaitingForResponse(false);

      // Remove "Bot: " prefix if present
      let botMessageText = message;
      if (message.startsWith("Bot: ")) {
        botMessageText = message.substring(5);
      }

      // Add message to chat history
      setChatHistory((prev) => {
        const lastMessage = prev[prev.length - 1];
        // If there's a loading placeholder, replace it with the actual message
        if (lastMessage && lastMessage.role === "model" && lastMessage.loading) {
          const updatedHistory = [...prev];
          updatedHistory[prev.length - 1] = {
            role: "model",
            text: botMessageText,
          };
          return updatedHistory;
        } else {
          return [...prev, { role: "model", text: botMessageText }];
        }
      });
    };
  }, [user]);  // Re-connect if user changes

  // Connect to WebSocket when component mounts
  useEffect(() => {
    connectWebSocket();
    // Clean up: close WebSocket when component unmounts
    return () => {
      ws.current?.close();
    };
  }, [connectWebSocket]);

  /**
   * Send a message to the backend via WebSocket.
   */
  const generateBotResponse = useCallback((userMessage) => {
    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      setIsWaitingForResponse(true);
      ws.current.send(userMessage);
    } else {
      console.error("WebSocket is not connected.");
      setChatHistory((prev) => [
        ...prev,
        { role: "model", text: "Cannot send message. Not connected." },
      ]);
      setIsWaitingForResponse(false);
      setChatHistory((prev) =>
        prev.filter((msg) => !(msg.role === "model" && msg.loading))
      );
    }
  }, []);

  return (
    <>
      <NavHeader />
      <div className="container">
        <div className="chatbot-popup">
          <div className="chat-header">
            <div className="header-info">
              <ChatbotIcon />
              <h2 className="logo-text">Healthcare Chatbot</h2>
            </div>
            <span
              style={{
                color: isConnected ? "lightgreen" : "tomato",
                marginRight: "10px",
                fontSize: "0.8em",
              }}
            >
              {isConnected ? "Connected" : "Disconnected"}
            </span>
            <button className="material-symbols-rounded">
              keyboard_arrow_down
            </button>
          </div>

          <div className="chat-body" ref={chatBodyRef}>
            {chatHistory.map((chat, index) => (
              <ChatMessage key={index} chat={chat} />
            ))}
          </div>

          <div className="chat-footer">
            <ChatForm
              chatHistory={chatHistory}
              setChatHistory={setChatHistory}
              generateBotResponse={generateBotResponse}
              isWaitingForResponse={isWaitingForResponse}
            />
          </div>
        </div>
      </div>
    </>
  );
};

// Layout wrapper for patient pages with navigation
const PatientLayout = ({ children }) => {
  return (
    <div className="patient-layout">
      <NavHeader />
      <div className="patient-content">
        {children}
      </div>
    </div>
  );
};

const App = () => {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          {/* Public routes */}
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          
          {/* Patient routes - wrapped with PatientLayout */}
          <Route path="/" element={
            <ProtectedRoute allowedRoles={['patient', 'admin']}>
              <ChatApp />
            </ProtectedRoute>
          } />
          <Route path="/my-reservations" element={
            <ProtectedRoute allowedRoles={['patient', 'admin']}>
              <PatientLayout>
                <MyReservations />
              </PatientLayout>
            </ProtectedRoute>
          } />
          <Route path="/doctors" element={
            <ProtectedRoute allowedRoles={['patient', 'admin']}>
              <PatientLayout>
                <Doctors />
              </PatientLayout>
            </ProtectedRoute>
          } />
          
          {/* Doctor routes - no wrapper, they have their own full-screen layout */}
          <Route path="/doctor/dashboard" element={
            <ProtectedRoute allowedRoles={['doctor', 'admin']}>
              <DoctorDashboard />
            </ProtectedRoute>
          } />
          <Route path="/doctor/patients" element={
            <ProtectedRoute allowedRoles={['doctor', 'admin']}>
              <DoctorPatients />
            </ProtectedRoute>
          } />
          <Route path="/doctor/appointments" element={
            <ProtectedRoute allowedRoles={['doctor', 'admin']}>
              <DoctorAppointments />
            </ProtectedRoute>
          } />
          <Route path="/doctor/patient/:patientName" element={
            <ProtectedRoute allowedRoles={['doctor', 'admin']}>
              <PatientDetail />
            </ProtectedRoute>
          } />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
};

export default App;
