// src/App.js

import React from 'react';
import { Routes, Route } from 'react-router-dom';
import Login from '../components/Login';
import Home from '../components/Home';
import Chat from '../components/Chat';
import ProtectedRoute from '../components/ProtectedRoute';
import SignUp from '../components/SignUp'; // Import the SignUp component

function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/signup" element={<SignUp />} /> {/* Add this line */}
      <Route
        path="/chat/:roomid"
        element={
          <ProtectedRoute>
            <Chat />
          </ProtectedRoute>
        }
      />
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <Home />
          </ProtectedRoute>
        }
      />
      {/* Add more routes as needed */}
    </Routes>
  );
}

export default App;
