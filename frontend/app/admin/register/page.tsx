'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useAuth } from '@/contexts/AuthContext';
import axios from 'axios';
import { API_ENDPOINTS } from '@/lib/api';

export default function AdminRegisterPage() {
  const { token, user } = useAuth();
  const [formData, setFormData] = useState({
    email: '',
    voter_id: '',
    password: '',
    role: 'voter'
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      await axios.post(
        API_ENDPOINTS.REGISTER,
        formData,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setSuccess(true);
      setFormData({ email: '', voter_id: '', password: '', role: 'voter' });
      setTimeout(() => setSuccess(false), 3000);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Registration failed');
    } finally {
      setLoading(false);
    }
  };

  if (!user?.is_admin) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="bg-red-500/10 border border-red-500/50 rounded-2xl p-8 text-center">
          <h2 className="text-2xl font-bold text-red-400 mb-2">Access Denied</h2>
          <p className="text-slate-400">Only administrators can register users</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen">
      <header className="bg-slate-900/80 backdrop-blur-md border-b border-slate-700">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <Link href="/admin" className="text-emerald-400 hover:text-emerald-300">
              ← Back to Admin
            </Link>
          </div>
        </div>
      </header>

      <main className="max-w-md mx-auto px-4 py-12">
        <div className="bg-slate-800/50 border border-slate-700 rounded-2xl p-8">
          <h1 className="text-2xl font-bold text-white mb-6">Register New User</h1>

          {success && (
            <div className="bg-emerald-500/10 border border-emerald-500/50 text-emerald-400 px-4 py-3 rounded-lg mb-6">
              User registered successfully!
            </div>
          )}

          {error && (
            <div className="bg-red-500/10 border border-red-500/50 text-red-400 px-4 py-3 rounded-lg mb-6">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-slate-300 mb-2">Email</label>
              <input
                type="email"
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                className="w-full bg-slate-900 border border-slate-600 rounded-lg px-4 py-3 text-white"
                required
              />
            </div>

            <div>
              <label className="block text-slate-300 mb-2">Voter ID</label>
              <input
                type="text"
                value={formData.voter_id}
                onChange={(e) => setFormData({ ...formData, voter_id: e.target.value })}
                className="w-full bg-slate-900 border border-slate-600 rounded-lg px-4 py-3 text-white"
                required
              />
            </div>

            <div>
              <label className="block text-slate-300 mb-2">Password</label>
              <input
                type="password"
                value={formData.password}
                onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                className="w-full bg-slate-900 border border-slate-600 rounded-lg px-4 py-3 text-white"
                required
                minLength={8}
              />
              <p className="text-slate-500 text-xs mt-1">Min 8 chars, 1 upper, 1 lower, 1 digit</p>
            </div>

            <div>
              <label className="block text-slate-300 mb-2">Role</label>
              <select
                value={formData.role}
                onChange={(e) => setFormData({ ...formData, role: e.target.value })}
                className="w-full bg-slate-900 border border-slate-600 rounded-lg px-4 py-3 text-white"
              >
                <option value="voter">Voter</option>
                {user?.role === 'superadmin' && (
                  <>
                    <option value="admin">Admin</option>
                    <option value="superadmin">Superadmin</option>
                  </>
                )}
              </select>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-emerald-600 hover:bg-emerald-700 disabled:bg-slate-700 text-white font-bold py-3 rounded-lg transition"
            >
              {loading ? 'Registering...' : 'Register User'}
            </button>
          </form>
        </div>
      </main>
    </div>
  );
}
