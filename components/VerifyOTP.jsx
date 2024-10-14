// src/components/VerifyOTP.jsx

import React, { useState } from 'react';
import axios from 'axios';
import { Link } from 'react-router-dom';

function VerifyOTP({ email }) {
  const [otp, setOTP] = useState('');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [isVerified, setIsVerified] = useState(false);

  const handleVerify = async (e) => {
    e.preventDefault();
    setMessage('');
    setError('');

    if (!otp) {
      setError('Please enter the OTP.');
      return;
    }

    try {
      const response = await axios.post('http://localhost:5000/api/verify-otp', {
        email,
        otp,
      }, {
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (response.status === 200) {
        setMessage('Account verified successfully! You can now log in.');
        setIsVerified(true);
      }
    } catch (err) {
      if (err.response && err.response.data && err.response.data.msg) {
        setError(err.response.data.msg);
      } else {
        setError('An error occurred during verification.');
      }
    }
  };

  const handleResendOTP = async () => {
    setMessage('');
    setError('');

    try {
      const response = await axios.post('http://localhost:5000/api/resend-otp', {
        email,
      }, {
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (response.status === 200) {
        setMessage('OTP resent successfully! Please check your email.');
      }
    } catch (err) {
      if (err.response && err.response.data && err.response.data.msg) {
        setError(err.response.data.msg);
      } else {
        setError('An error occurred while resending OTP.');
      }
    }
  };

  if (isVerified) {
    return (
      <div className="flex items-center justify-center h-screen bg-gray-100">
        <div className="bg-white p-6 rounded shadow-md w-96 text-center">
          <h1 className="text-2xl mb-4">Verification Successful</h1>
          <p className="mb-4">Your account has been verified. You can now <Link to="/login" className="text-blue-500 hover:underline">log in</Link>.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex items-center justify-center h-screen bg-gray-100">
      <form
        onSubmit={handleVerify}
        className="bg-white p-6 rounded shadow-md w-96"
      >
        <h1 className="text-2xl mb-4">Verify OTP</h1>
        {message && <div className="text-green-500 mb-2">{message}</div>}
        {error && <div className="text-red-500 mb-2">{error}</div>}
        <div className="mb-4">
          <label className="block mb-1">Email:</label>
          <input
            type="email"
            className="w-full border px-3 py-2 rounded"
            value={email}
            disabled
          />
        </div>
        <div className="mb-4">
          <label className="block mb-1">Enter OTP:</label>
          <input
            type="text"
            className="w-full border px-3 py-2 rounded"
            value={otp}
            onChange={(e) => setOTP(e.target.value)}
            required
            placeholder="Enter the OTP sent to your email"
          />
        </div>
        <button
          type="submit"
          className="w-full bg-blue-500 text-white py-2 rounded hover:bg-blue-600 transition duration-200"
        >
          Verify
        </button>
        <button
          type="button"
          onClick={handleResendOTP}
          className="w-full mt-2 bg-gray-500 text-white py-2 rounded hover:bg-gray-600 transition duration-200"
        >
          Resend OTP
        </button>
      </form>
    </div>
  );
}

export default VerifyOTP;
