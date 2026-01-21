import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';

// Backend API URL (reads port from environment variable or defaults to 8000)
const API_BASE = `http://localhost:${import.meta.env.VITE_API_PORT || 8000}`;

// =============================================================================
// AUTH CONTEXT
// =============================================================================
// React Context is like a "global state" that can be accessed from any component.
// AuthContext stores the current user's login state so any component can check
// if the user is logged in without passing props down through every component.

const AuthContext = createContext(null);

/**
 * Custom hook to access the auth context.
 * Usage in any component: const { user, login, logout } = useAuth();
 */
export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

/**
 * AuthProvider wraps the entire app and provides auth state to all components.
 * 
 * How it works:
 * 1. When app loads, checkAuth() asks the backend "am I logged in?"
 * 2. The backend checks the session cookie and returns user info (or error)
 * 3. This state is stored in React and shared with all child components
 */
export const AuthProvider = ({ children }) => {
  // State variables
  const [user, setUser] = useState(null);         // Current logged-in user
  const [doctorInfo, setDoctorInfo] = useState(null);  // Extra info if user is a doctor
  const [loading, setLoading] = useState(true);   // True while checking auth status
  const [error, setError] = useState(null);       // Error message if something fails

  /**
   * Check if user is currently authenticated.
   * Called when the app first loads and after login.
   * 
   * credentials: 'include' tells the browser to send cookies with the request.
   * 
   */
  const checkAuth = useCallback(async () => {//without usecallback each time that there is a render this function is re-created
    try {
      const response = await fetch(`${API_BASE}/api/auth/me`, {
        credentials: 'include'  // Send session cookie with request
      });

      if (response.ok) {
        const data = await response.json();
        if (data.authenticated) {
          setUser(data.user);
          setDoctorInfo(data.doctor_info);
        } else {
          setUser(null);
          setDoctorInfo(null);
        }
      } else {
        setUser(null);
        setDoctorInfo(null);
      }
    } catch (err) {
      console.error('Auth check failed:', err);
      setUser(null);
      setDoctorInfo(null);
    } finally {
      setLoading(false);
    }
  }, []);

  // Check auth status when component mounts (app starts)
  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  /**
   * Log in with username and password.
   * On success, the backend sets a session cookie automatically.
   */
  const login = async (username, password) => {
    setError(null);
    
    try {
      const response = await fetch(`${API_BASE}/api/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',  // Important: receive and store the session cookie
        body: JSON.stringify({ username, password }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || 'Login failed');
      }

      // Save user to state
      setUser(data.user);
      
      // If the user is a doctor, get their doctor profile info
      if (data.user.role === 'doctor') {
        await checkAuth();
      }

      return { success: true, user: data.user };
    } catch (err) {
      setError(err.message);
      return { success: false, error: err.message };
    }
  };

  /**
   * Register a new user account.
   */
  const register = async (userData) => {
    setError(null);
    
    try {
      const response = await fetch(`${API_BASE}/api/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(userData),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || 'Registration failed');
      }

      return { success: true, userId: data.user_id };
    } catch (err) {
      setError(err.message);
      return { success: false, error: err.message };
    }
  };

  /**
   * Log out the current user.
   * The backend clears the session, and we clear local state.
   */
  const logout = async () => {
    try {
      await fetch(`${API_BASE}/api/auth/logout`, {
        method: 'POST',
        credentials: 'include'  // Send session cookie so backend knows who to log out
      });
    } catch (err) {
      console.error('Logout error:', err);
    } finally {
      // Clear all local state
      setUser(null);
      setDoctorInfo(null);
      // Clear any cached chat history from localStorage
      localStorage.removeItem('medassist_chat_history');
      localStorage.removeItem('medassist_current_user');
    }
  };

  // Convenience booleans for checking user roles
  const isAuthenticated = !!user;
  const isDoctor = user?.role === 'doctor';
  const isAdmin = user?.role === 'admin';
  const isPatient = user?.role === 'patient';

  // Values that will be available to all components via useAuth()
  const value = {
    user,
    doctorInfo,
    loading,
    error,
    login,
    register,
    logout,
    checkAuth,
    isAuthenticated,
    isDoctor,
    isAdmin,
    isPatient,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export default AuthContext;
