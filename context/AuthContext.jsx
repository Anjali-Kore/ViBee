// src/context/AuthContext.js

import React, { createContext, useState, useEffect } from 'react';
import jwtDecode from 'jwt-decode';
import { useNavigate } from 'react-router-dom';

export const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
  const navigate = useNavigate();
  const [auth, setAuth] = useState({
    token: null,
    user: null,
  });

  useEffect(() => {
    // On component mount, check if token exists
    const token = localStorage.getItem('token');
    if (token) {
      try {
        const decoded = jwtDecode(token);
        setAuth({
          token,
          user: decoded,
        });
      } catch (e) {
        console.error('Invalid token');
        localStorage.removeItem('token');
      }
    }
  }, []);

  const login = (token) => {
    try {
      const decoded = jwtDecode(token);
      setAuth({
        token,
        user: decoded,
      });
      localStorage.setItem('token', token);
    } catch (e) {
      console.error('Invalid token');
    }
  };

  const logout = () => {
    setAuth({
      token: null,
      user: null,
    });
    localStorage.removeItem('token');
    navigate('/login');
  };

  return (
    <AuthContext.Provider value={{ auth, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
};
