'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/contexts/AuthContext';
import axios from 'axios';

interface PendingAspirant {
  candidate_id: string;
  name: string;
  party: string;
  manifesto: string;
  created_at: string;
}

export default function PendingAspirantsPage() {
  const { user, isAuthenticated, isLoading, token } = useAuth();
  const router = useRouter();
  const [aspirants, setAspirants] = useState<PendingAspirant[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  useEffect(() => {
    if (!isLoading && (!isAuthenticated || !user?.is_admin)) {
      router.push('/');
    }
  }, [isLoading, isAuthenticated, user, router]);

  useEffect(() => {
    if (token && user?.is_admin) {
      fetchPendingAspirants();
    }
  }, [token, user]);

  const fetchPendingAspirants = async () => {
    if (!token) return;
    try {
      const response = await axios.get('http://localhost:8000/api/v1/aspirant/pending', {
        headers: { Authorization: `Bearer ${token}` }
      });
      setAspirants(response.data.pending_aspirants);
    } catch (error) {
      console.error('Error fetching pending aspirants:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleApprove = async (candidateId: string) => {
    if (!token) return;
    setActionLoading(`approve-${candidateId}`);
    try {
      await axios.post(`http://localhost:8000/api/v1/aspirant/${candidateId}/approve`, {}, {
        headers: { Authorization: `Bearer ${token}` }
      });
      alert('Aspirant approved successfully');
      fetchPendingAspirants();
    } catch (error) {
      alert('Failed to approve aspirant');
    } finally {
      setActionLoading(null);
    }
  };

  const handleReject = async (candidateId: string) => {
    if (!token) return;
    const reason = prompt('Reason for rejection (optional):');
    setActionLoading(`reject-${candidateId}`);
    try {
      await axios.post(`http://localhost:8000/api/v1/aspirant/${candidateId}/reject`, 
        { reason },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      alert('Aspirant rejected');
      fetchPendingAspirants();
    } catch (error) {
      alert('Failed to reject aspirant');
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

  return (
    <div className="min-h-screen">
      <header className="bg-slate-900/80 backdrop-blur-md border-b border-slate-700">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <Link href="/admin" className="flex items-center space-x-2">
              <div className="w-8 h-8 bg-purple-500 rounded-lg flex items-center justify-center">
                <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
              </div>
              <span className="text-xl font-bold text-white">Pending Aspirants</span>
            </Link>
            <Link href="/admin" className="text-slate-300 hover:text-emerald-400 transition">Back to Admin</Link>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <h1 className="text-3xl font-bold text-white mb-8">Pending Aspirant Applications</h1>

        {aspirants.length === 0 ? (
          <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-12 text-center">
            <div className="text-6xl mb-4">✅</div>
            <h2 className="text-xl font-semibold text-white mb-2">No Pending Applications</h2>
            <p className="text-slate-400">All aspirant applications have been reviewed</p>
          </div>
        ) : (
          <div className="space-y-6">
            {aspirants.map((aspirant) => (
              <div key={aspirant.candidate_id} className="bg-slate-800/50 border border-slate-700 rounded-xl p-6">
                <div className="flex justify-between items-start mb-4">
                  <div>
                    <h3 className="text-xl font-bold text-white mb-1">{aspirant.name}</h3>
                    <p className="text-slate-400 text-sm">ID: {aspirant.candidate_id}</p>
                    {aspirant.party && (
                      <p className="text-emerald-400 text-sm mt-1">Party: {aspirant.party}</p>
                    )}
                  </div>
                  <span className="bg-yellow-500/20 text-yellow-400 px-3 py-1 rounded-full text-sm">
                    Pending
                  </span>
                </div>

                <div className="mb-4">
                  <h4 className="text-slate-300 font-semibold mb-2">Manifesto:</h4>
                  <p className="text-slate-400 whitespace-pre-wrap">{aspirant.manifesto}</p>
                </div>

                <div className="text-slate-500 text-sm mb-4">
                  Applied: {new Date(aspirant.created_at).toLocaleString()}
                </div>

                <div className="flex space-x-4">
                  <button
                    onClick={() => handleApprove(aspirant.candidate_id)}
                    disabled={actionLoading === `approve-${aspirant.candidate_id}`}
                    className="bg-emerald-600 hover:bg-emerald-700 disabled:bg-slate-600 text-white px-6 py-2 rounded-lg transition"
                  >
                    {actionLoading === `approve-${aspirant.candidate_id}` ? 'Approving...' : 'Approve'}
                  </button>
                  <button
                    onClick={() => handleReject(aspirant.candidate_id)}
                    disabled={actionLoading === `reject-${aspirant.candidate_id}`}
                    className="bg-red-600 hover:bg-red-700 disabled:bg-slate-600 text-white px-6 py-2 rounded-lg transition"
                  >
                    {actionLoading === `reject-${aspirant.candidate_id}` ? 'Rejecting...' : 'Reject'}
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
