// src/components/Home.js

import React, { useState, useEffect, useContext } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import jwtDecode from 'jwt-decode';
import { AuthContext } from '../context/AuthContext';
import { FiLogOut, FiPlus, FiMessageSquare } from 'react-icons/fi'; // Importing icons for better UI

function Home() {
  const [username, setUsername] = useState('Guest');
  const [roomid, setRoomid] = useState('');
  const [recentRooms, setRecentRooms] = useState([]);
  const [error, setError] = useState('');
  const navigate = useNavigate();
  const { auth, logout } = useContext(AuthContext);

  useEffect(() => {
    const token = auth.token;
    if (token) {
      try {
        const decoded = jwtDecode(token);
        setUsername(decoded.sub);
      } catch (e) {
        console.error('Invalid token');
        logout(); // Logout if token is invalid
      }
    }
  }, [auth.token, logout]);

  useEffect(() => {
    const fetchRecentRooms = async () => {
      const token = auth.token;
      if (!token) return;

      try {
        const response = await axios.get('http://localhost:5000/api/recent_rooms', {
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        });
        setRecentRooms(response.data.recent_rooms);
      } catch (err) {
        console.error('Error fetching recent rooms:', err);
      }
    };

    fetchRecentRooms();
  }, [auth.token]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (roomid.trim()) {
      navigate(`/chat/${roomid}`);
    }
  };

  const handleLogout = () => {
    logout();
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-500 to-indigo-600 flex flex-col items-center p-6 sm:p-12">
      {/* Header */}
      <div className="w-full max-w-4xl flex flex-col sm:flex-row justify-between items-center mb-8 space-x-3">
        {/* Logout Button */}
        <button
          onClick={handleLogout}
          className="flex items-center bg-red-500 text-white px-2 py-1 md:px-4 md:py-2 rounded mb-4 sm:mb-0 hover:bg-red-600 transition duration-200"
        >
          <FiLogOut className="mr-2" /> Logout
        </button>

        {/* Application Title */}
        <h1 className="text-4xl font-bold text-white hover:text-gray-200 transition duration-200 mb-4 sm:mb-0">
          ViBee
        </h1>

        {/* User Greeting */}
        <div className="text-white text-sm flex md:text-lg">
          Hello, <span className="font-semibold">{username}</span>
        </div>
      </div>

      {/* Recent Rooms */}
      <div className="w-full max-w-4xl mb-8 px-4 sm:px-0">
        <h2 className="text-2xl font-semibold text-white mb-4 flex items-center">
          <FiMessageSquare className="mr-2" /> Recently Joined Rooms
        </h2>
        {recentRooms.length > 0 ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {recentRooms.slice(0, 3).map((room, index) => (
              <div
                key={index}
                className="bg-white bg-opacity-90 rounded-lg shadow-md p-6 flex flex-col justify-between hover:bg-opacity-100 transition duration-200"
              >
                <div className="mb-4">
                  <h3 className="text-xl font-semibold text-gray-800">{room}</h3>
                  <p className="text-gray-600">Join the conversation now!</p>
                </div>
                <button
                  onClick={() => navigate(`/chat/${room}`)}
                  className="mt-auto flex items-center justify-center bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600 transition duration-200 w-full"
                >
                  Join Room
                </button>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-white">No recently joined rooms.</p>
        )}
      </div>

      {/* Join Room Form */}
      <form onSubmit={handleSubmit} className="w-full max-w-md bg-white bg-opacity-90 rounded-lg shadow-md p-6 sm:p-8">
        <h2 className="text-2xl font-semibold text-gray-800 mb-4 flex items-center">
          <FiPlus className="mr-2" /> Join a New Room
        </h2>
        {error && <div className="text-red-500 mb-2">{error}</div>}
        <div className="flex flex-col sm:flex-row items-stretch">
          <input
            type="text"
            name="roomid"
            className="flex-grow border border-gray-300 px-4 py-2 rounded sm:rounded-r-none focus:outline-none focus:ring-2 focus:ring-blue-500 mb-4 sm:mb-0 sm:mr-2"
            value={roomid}
            onChange={(e) => setRoomid(e.target.value)}
            required
            placeholder="Enter Room ID"
          />
          <button
            type="submit"
            className="bg-green-500 text-white px-4 py-2 rounded sm:rounded-l-none hover:bg-green-600 transition duration-200 w-full sm:w-auto flex items-center justify-center"
          >
            Join
          </button>
        </div>
      </form>
    </div>
  );
}

export default Home;
