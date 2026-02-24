'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/contexts/AuthContext';
import axios from 'axios';
import { API_ENDPOINTS } from '@/lib/api';

interface User {
  id: number;
  email: string;
  voter_id: string;
  has_voted: boolean;
  is_admin: boolean;
  created_at: string;
}

interface Stats {
  total_users: number;
  total_votes: number;
  banned_ips: number;
  active_users_24h: number;
}

interface IPLog {
  ip_address: string;
  banned_until: string;
  reason: string | null;
  failed_attempts: number;
}

export default function AdminPage() {
  const { user, isAuthenticated, isLoading, token, logout } = useAuth();
  const router = useRouter();
  const [stats, setStats] = useState<Stats | null>(null);
  const [users, setUsers] = useState<User[]>([]);
  const [bannedIPs, setBannedIPs] = useState<IPLog[]>([]);
  const [activeTab, setActiveTab] = useState('overview');
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  useEffect(() => {
    if (!isLoading && (!isAuthenticated || !user?.is_admin)) {
      router.push('/');
    }
  }, [isLoading, isAuthenticated, user, router]);

  useEffect(() => {
    if (token && user?.is_admin) {
      fetchData();
    }
  }, [token, user]);

  const fetchData = async () => {
    if (!token) return;
    try {
      const [statsRes, usersRes] = await Promise.all([
        axios.get(API_ENDPOINTS.ADMIN_STATS, { headers: { Authorization: `Bearer ${token}` } }),
        axios.get(API_ENDPOINTS.ADMIN_USERS, { headers: { Authorization: `Bearer ${token}` } })
      ]);
      setStats(statsRes.data);
      setUsers(usersRes.data);
    } catch (error) {
      console.error('Error fetching admin data:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchBannedIPs = async () => {
    if (!token) return;
    try {
      const response = await axios.get(API_ENDPOINTS.ADMIN_BANNED_IPS, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setBannedIPs(response.data);
    } catch (error) {
      console.error('Error fetching banned IPs:', error);
    }
  };

  const resetDevice = async (userId: number) => {
    if (!token) return;
    setActionLoading(`reset-${userId}`);
    try {
      await axios.post(API_ENDPOINTS.ADMIN_RESET_DEVICE(userId), {}, {
        headers: { Authorization: `Bearer ${token}` }
      });
      alert('Device reset successfully');
      fetchData();
    } catch (error) {
      alert('Failed to reset device');
    } finally {
      setActionLoading(null);
    }
  };

  const unbanIP = async (ip: string) => {
    if (!token) return;
    setActionLoading(`unban-${ip}`);
    try {
      await axios.post(API_ENDPOINTS.ADMIN_UNBAN_IP, { ip_address: ip }, {
        headers: { Authorization: `Bearer ${token}` }
      });
      alert('IP unbanned successfully');
      fetchBannedIPs();
    } catch (error) {
      alert('Failed to unban IP');
    } finally {
      setActionLoading(null);
    }
  };

  if (isLoading || loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-emerald-500"></div>
      </div>
    );
  }

  if (!user?.is_admin) {
    return null;
  }

  return (
    <div className="min-h-screen">
      {/* Header */}
      <header className="bg-slate-900/80 backdrop-blur-md border-b border-slate-700">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <Link href="/" className="flex items-center space-x-2">
              <div className="w-8 h-8 bg-purple-500 rounded-lg flex items-center justify-center">
                <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
              </div>
              <span className="text-xl font-bold text-white">Admin Panel</span>
            </Link>
            
            <div className="flex items-center space-x-4">
              <Link href="/dashboard" className="text-slate-300 hover:text-emerald-400 transition">Dashboard</Link>
              <button 
                onClick={() => { logout(); router.push('/'); }}
                className="bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded-lg transition"
              >
                Logout
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <h1 className="text-3xl font-bold text-white mb-8">Admin Dashboard</h1>

        {/* Tabs */}
        <div className="flex space-x-4 mb-8">
          {['overview', 'users', 'security', 'register'].map((tab) => (
            <button
              key={tab}
              onClick={() => {
                if (tab === 'register') {
                  router.push('/admin/register');
                } else {
                  setActiveTab(tab);
                }
              }}
              className={`px-4 py-2 rounded-lg transition ${
                activeTab === tab 
                  ? 'bg-purple-600 text-white' 
                  : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
              }`}
            >
              {tab.charAt(0).toUpperCase() + tab.slice(1)}
            </button>
          ))}
        </div>

        {/* Overview Tab */}
        {activeTab === 'overview' && stats && (
          <div className="grid md:grid-cols-4 gap-6">
            <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6">
              <div className="text-3xl font-bold text-emerald-400">{stats.total_users}</div>
              <div className="text-slate-400">Total Users</div>
            </div>
            <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6">
              <div className="text-3xl font-bold text-emerald-400">{stats.total_votes}</div>
              <div className="text-slate-400">Total Votes</div>
            </div>
            <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6">
              <div className="text-3xl font-bold text-red-400">{stats.banned_ips}</div>
              <div className="text-slate-400">Banned IPs</div>
            </div>
            <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6">
              <div className="text-3xl font-bold text-emerald-400">{stats.active_users_24h}</div>
              <div className="text-slate-400">Active Users (24h)</div>
            </div>
          </div>
        )}

        {/* Users Tab */}
        {activeTab === 'users' && (
          <div className="bg-slate-800/50 border border-slate-700 rounded-xl overflow-hidden">
            <table className="w-full">
              <thead className="bg-slate-900/50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase">ID</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase">Email</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase">Voter ID</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase">Voted</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase">Admin</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-700">
                {users.map((u) => (
                  <tr key={u.id} className="hover:bg-slate-700/30">
                    <td className="px-6 py-4 text-white">{u.id}</td>
                    <td className="px-6 py-4 text-white">{u.email}</td>
                    <td className="px-6 py-4 text-white font-mono">{u.voter_id}</td>
                    <td className="px-6 py-4">
                      <span className={`px-2 py-1 rounded text-xs ${u.has_voted ? 'bg-green-500/20 text-green-400' : 'bg-yellow-500/20 text-yellow-400'}`}>
                        {u.has_voted ? 'Yes' : 'No'}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <span className={`px-2 py-1 rounded text-xs ${u.is_admin ? 'bg-purple-500/20 text-purple-400' : 'bg-slate-600 text-slate-300'}`}>
                        {u.is_admin ? 'Yes' : 'No'}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <button
                        onClick={() => resetDevice(u.id)}
                        disabled={actionLoading === `reset-${u.id}`}
                        className="text-purple-400 hover:text-purple-300 text-sm disabled:opacity-50"
                      >
                        {actionLoading === `reset-${u.id}` ? 'Resetting...' : 'Reset Device'}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Security Tab */}
        {activeTab === 'security' && (
          <div>
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xl font-semibold text-white">Banned IPs</h2>
              <button
                onClick={fetchBannedIPs}
                className="bg-slate-700 hover:bg-slate-600 text-white px-4 py-2 rounded-lg text-sm"
              >
                Refresh
              </button>
            </div>
            {bannedIPs.length === 0 ? (
              <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6 text-center">
                <p className="text-slate-400">No banned IPs</p>
              </div>
            ) : (
              <div className="space-y-2">
                {bannedIPs.map((ip) => (
                  <div key={ip.ip_address} className="bg-slate-800/50 border border-slate-700 rounded-xl p-4 flex justify-between items-center">
                    <div>
                      <div className="text-white font-mono">{ip.ip_address}</div>
                      <div className="text-slate-400 text-sm">
                        Banned until: {new Date(ip.banned_until).toLocaleString()} | Attempts: {ip.failed_attempts}
                      </div>
                    </div>
                    <button
                      onClick={() => unbanIP(ip.ip_address)}
                      disabled={actionLoading === `unban-${ip.ip_address}`}
                      className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg text-sm disabled:opacity-50"
                    >
                      {actionLoading === `unban-${ip.ip_address}` ? 'Unbanning...' : 'Unban'}
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
