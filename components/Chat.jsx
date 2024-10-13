// src/components/Chat.js

import React, { useEffect, useState, useContext, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import io from 'socket.io-client';
import jwtDecode from 'jwt-decode';
import axios from 'axios';
import { AuthContext } from '../context/AuthContext';

let socket;

function Chat() {
  const { roomid } = useParams();
  const navigate = useNavigate();
  const [messages, setMessages] = useState([]);
  const [messageInput, setMessageInput] = useState('');
  const [username, setUsername] = useState('');
  const { auth, logout } = useContext(AuthContext); // Access auth context

  const messagesEndRef = useRef(null);
  const messagesContainerRef = useRef(null);

  const [hasMore, setHasMore] = useState(true);
  const [loading, setLoading] = useState(false);
  const [offset, setOffset] = useState(0);
  const limit = 50; // Number of messages to fetch per request

  useEffect(() => {
    const token = auth.token;
    if (!token) {
      navigate('/login');
      return;
    }

    try {
      const decoded = jwtDecode(token);
      setUsername(decoded.sub);
    } catch (e) {
      console.error('Invalid token');
      logout(); // Logout the user if token is invalid
      navigate('/login');
      return;
    }

    // Initialize Socket.IO
    socket = io('http://localhost:5000', {
      auth: {
        token: token, // JWT token
      },
      transports: ['websocket', 'polling'],
    });

    socket.on('connect', () => {
      console.log('Connected to Socket.IO server');
      socket.emit('join_room', { roomid });
    });

    // Receive past messages
    socket.on('previous_messages', (data) => {
      if (data.messages && Array.isArray(data.messages)) {
        setMessages(data.messages);
        setOffset(offset + limit);
        if (data.messages.length < limit) {
          setHasMore(false);
        }
        scrollToBottom();
      }
    });

    // Receive new messages
    socket.on('receive_message', (data) => {
      setMessages((prev) => [...prev, {
        username: data.username,
        message: data.message,
        timestamp: data.timestamp,
      }]);
      scrollToBottom();
    });

    // Receive join room announcements
    socket.on('join_room_announcement', (data) => {
      setMessages((prev) => [...prev, {
        username: data.username,
        message: data.message,
        timestamp: new Date().toISOString(),
      }]);
      scrollToBottom();
    });

    socket.on('error', (data) => {
      console.error('Socket error:', data.msg);
      // Optionally, handle errors (e.g., redirect to login)
    });

    return () => {
      socket.disconnect();
    };
  }, [roomid, navigate, auth.token, logout]);

  useEffect(() => {
    // Fetch initial messages via API for pagination
    const fetchInitialMessages = async () => {
      setLoading(true);
      const token = auth.token;
      if (!token) return;

      try {
        const response = await axios.get(`http://localhost:5000/api/messages/${roomid}?limit=${limit}&offset=${offset}`, {
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        });
        const fetchedMessages = response.data.messages;
        setMessages(fetchedMessages);
        setOffset(offset + limit);
        if (fetchedMessages.length < limit) {
          setHasMore(false);
        }
        scrollToBottom();
      } catch (err) {
        console.error('Error fetching messages:', err);
      }
      setLoading(false);
    };

    fetchInitialMessages();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [roomid]);

  const loadOlderMessages = async () => {
    if (loading || !hasMore) return;
    setLoading(true);
    const token = auth.token;
    if (!token) return;

    try {
      const response = await axios.get(`http://localhost:5000/api/messages/${roomid}?limit=${limit}&offset=${offset}`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });
      const fetchedMessages = response.data.messages;
      setMessages(prev => [...fetchedMessages, ...prev]);
      setOffset(offset + limit);
      if (fetchedMessages.length < limit) {
        setHasMore(false);
      }
    } catch (err) {
      console.error('Error fetching older messages:', err);
    }
    setLoading(false);
  };

  const handleScroll = () => {
    if (messagesContainerRef.current.scrollTop === 0 && hasMore && !loading) {
      loadOlderMessages();
    }
  };

  const scrollToBottom = () => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (messageInput.trim()) {
      socket.emit('send_message', {
        roomid,
        message: messageInput.trim(),
      });
      setMessageInput('');
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-gray-100 p-6">
      <div className="flex justify-between items-center mb-4">
        <h1 className="text-2xl">Room: {roomid}</h1>
        <button
          onClick={() => navigate('/')}
          className="bg-red-500 text-white px-3 py-1 rounded hover:bg-red-600"
        >
          Leave Room
        </button>
      </div>
      <div
        className="flex-grow bg-white p-4 rounded shadow overflow-auto mb-4"
        ref={messagesContainerRef}
        onScroll={handleScroll}
      >
        {hasMore && (
          <button
            onClick={loadOlderMessages}
            disabled={loading}
            className="mb-2 px-3 py-1 bg-gray-300 text-gray-700 rounded"
          >
            {loading ? 'Loading...' : 'Load More'}
          </button>
        )}
        {messages.map((msg, index) => (
          <div key={index} className="mb-2">
            <span className="font-semibold">{msg.username}</span>: {msg.message}
            <div className="text-xs text-gray-500">{new Date(msg.timestamp).toLocaleString()}</div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>
      <form onSubmit={handleSubmit} className="flex">
        <input
          type="text"
          placeholder="Enter your message here"
          className="flex-grow border px-3 py-2 rounded-l"
          value={messageInput}
          onChange={(e) => setMessageInput(e.target.value)}
          required
        />
        <button
          type="submit"
          className="bg-blue-500 text-white px-4 py-2 rounded-r hover:bg-blue-600"
        >
          Send
        </button>
      </form>
    </div>
  );
}

export default Chat;
