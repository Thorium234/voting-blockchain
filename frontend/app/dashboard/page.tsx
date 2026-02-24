'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/contexts/AuthContext';
import axios from 'axios';
import { API_ENDPOINTS } from '@/lib/api';

export default function DashboardPage() {
  const { user, isAuthenticated, isLoading, logout, token } = useAuth();
  const router = useRouter();
  const [hasVoted, setHasVoted] = useState(false);
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [isLoading, isAuthenticated, router]);

  useEffect(() => {
    const checkVoted = async () => {
      if (token) {
        try {
          const response = await axios.get(API_ENDPOINTS.CHECK_VOTED, {
            headers: { Authorization: `Bearer ${token}` }
          });
          setHasVoted(response.data.has_voted);
        } catch (error) {
          console.error('Error checking vote status:', error);
        } finally {
          setChecking(false);
        }
      }
    };

    if (token) {
      checkVoted();
    }
  }, [token]);

  if (isLoading || checking) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-emerald-500"></div>
      </div>
    );
  }

  if (!user) return null;

  return (
    <div className="min-h-screen">
      {/* Header */}
      <header className="bg-slate-900/80 backdrop-blur-md border-b border-slate-700">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center space-x-2">
              <Link href="/" className="flex items-center space-x-2">
                <div className="w-8 h-8 bg-emerald-500 rounded-lg flex items-center justify-center">
                  <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                  </svg>
                </div>
                <span className="text-xl font-bold text-white">BlockchainVote</span>
              </Link>
            </div>
            
            <div className="flex items-center space-x-4">
              <span className="text-slate-300">{user.email}</span>
              {user.is_admin && (
                <Link href="/admin" className="bg-purple-600 hover:bg-purple-700 text-white px-4 py-2 rounded-lg transition">
                  Admin
                </Link>
              )}
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
        <h1 className="text-3xl font-bold text-white mb-8">Dashboard</h1>

        {/* User Info Card */}
        <div className="bg-slate-800/50 border border-slate-700 rounded-2xl p-6 mb-8">
          <h2 className="text-xl font-semibold text-white mb-4">Your Information</h2>
          <div className="grid md:grid-cols-2 gap-4">
            <div>
              <p className="text-slate-400 text-sm">Email</p>
              <p className="text-white font-medium">{user.email}</p>
            </div>
            <div>
              <p className="text-slate-400 text-sm">Voter ID</p>
              <p className="text-white font-medium">{user.voter_id}</p>
            </div>
            <div>
              <p className="text-slate-400 text-sm">Account Type</p>
              <p className="text-white font-medium">{user.is_admin ? 'Administrator' : 'Voter'}</p>
            </div>
            <div>
              <p className="text-slate-400 text-sm">Registration Date</p>
              <p className="text-white font-medium">{new Date(user.created_at).toLocaleDateString()}</p>
            </div>
          </div>
        </div>

        {/* Voting Status */}
        <div className="bg-slate-800/50 border border-slate-700 rounded-2xl p-6 mb-8">
          <h2 className="text-xl font-semibold text-white mb-4">Voting Status</h2>
          
          {hasVoted ? (
            <div className="bg-emerald-500/10 border border-emerald-500/50 rounded-xl p-6 text-center">
              <div className="text-5xl mb-4">✅</div>
              <h3 className="text-xl font-semibold text-emerald-400 mb-2">You Have Voted!</h3>
              <p className="text-slate-400">Thank you for participating in this election. Your vote has been recorded on the blockchain.</p>
              <Link href="/results" className="inline-block mt-4 bg-emerald-600 hover:bg-emerald-700 text-white px-6 py-2 rounded-lg transition">
                View Results
              </Link>
            </div>
          ) : (
            <div className="bg-amber-500/10 border border-amber-500/50 rounded-xl p-6 text-center">
              <div className="text-5xl mb-4">🗳️</div>
              <h3 className="text-xl font-semibold text-amber-400 mb-2">You Haven't Voted Yet</h3>
              <p className="text-slate-400 mb-4">Your voice matters! Cast your vote now to participate in this election.</p>
              <Link href="/vote" className="inline-block bg-emerald-600 hover:bg-emerald-700 text-white px-6 py-2 rounded-lg transition">
                Cast Your Vote
              </Link>
            </div>
          )}
        </div>

        {/* Quick Actions */}
        <div className="grid md:grid-cols-3 gap-6">
          {user?.role === 'voter' && !hasVoted && (
            <Link href="/vote" className="bg-slate-800/50 border border-slate-700 hover:border-emerald-500 rounded-2xl p-6 transition group">
              <div className="text-4xl mb-4 group-hover:scale-110 transition">🗳️</div>
              <h3 className="text-lg font-semibold text-white mb-2">Cast Vote</h3>
              <p className="text-slate-400">Submit your vote for your preferred candidate</p>
            </Link>
          )}
          
          {user?.role !== 'voter' && (
            <Link href="/admin" className="bg-slate-800/50 border border-slate-700 hover:border-purple-500 rounded-2xl p-6 transition group">
              <div className="text-4xl mb-4 group-hover:scale-110 transition">⚙️</div>
              <h3 className="text-lg font-semibold text-white mb-2">Admin Panel</h3>
              <p className="text-slate-400">Manage voters, aspirants, and elections</p>
            </Link>
          )}
          
          <Link href="/results" className="bg-slate-800/50 border border-slate-700 hover:border-emerald-500 rounded-2xl p-6 transition group">
            <div className="text-4xl mb-4 group-hover:scale-110 transition">📊</div>
            <h3 className="text-lg font-semibold text-white mb-2">View Results</h3>
            <p className="text-slate-400">See live voting results and statistics</p>
          </Link>
          
          <Link href="/dashboard" className="bg-slate-800/50 border border-slate-700 hover:border-emerald-500 rounded-2xl p-6 transition group">
            <div className="text-4xl mb-4 group-hover:scale-110 transition">🔗</div>
            <h3 className="text-lg font-semibold text-white mb-2">Blockchain</h3>
            <p className="text-slate-400">View the blockchain and verify your vote</p>
          </Link>
        </div>
      </main>
    </div>
  );
}
