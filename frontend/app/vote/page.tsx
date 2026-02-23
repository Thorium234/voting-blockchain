'use client';
'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/contexts/AuthContext';
import axios from 'axios';
import { API_ENDPOINTS } from '@/lib/api';

interface Candidate {
  id: string;
  name: string;
  party: string;
  description: string;
}

const candidates: Candidate[] = [
  { id: 'candidate_a', name: 'Candidate A', party: 'Party Alpha', description: 'Experienced leader with a vision for progress' },
  { id: 'candidate_b', name: 'Candidate B', party: 'Party Beta', description: 'Champion of change and innovation' },
  { id: 'candidate_c', name: 'Candidate C', party: 'Party Gamma', description: 'Dedicated to serving the community' },
];

export default function VotePage() {
  const { user, isAuthenticated, isLoading, token } = useAuth();
  const router = useRouter();
  const [selectedCandidate, setSelectedCandidate] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);
  const [hasVoted, setHasVoted] = useState(false);

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
          if (response.data.has_voted) {
            setHasVoted(true);
          }
        } catch (error) {
          console.error('Error checking vote status:', error);
        }
      }
    };

    if (token) {
      checkVoted();
    }
  }, [token]);

  const handleVote = async () => {
    if (!selectedCandidate) {
      setError('Please select a candidate');
      return;
    }

    setError('');
    setLoading(true);

    try {
      await axios.post(
        API_ENDPOINTS.VOTE,
        { candidate_id: selectedCandidate },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setSuccess(true);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to cast vote. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  if (isLoading || hasVoted) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        {hasVoted ? (
          <div className="bg-emerald-500/10 border border-emerald-500/50 rounded-2xl p-8 text-center max-w-md">
            <div className="text-6xl mb-4">✅</div>
            <h2 className="text-2xl font-bold text-emerald-400 mb-2">You Have Already Voted</h2>
            <p className="text-slate-400 mb-6">Your vote has been recorded on the blockchain.</p>
            <Link href="/results" className="bg-emerald-600 hover:bg-emerald-700 text-white px-6 py-3 rounded-lg transition">
              View Results
            </Link>
          </div>
        ) : (
          <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-emerald-500"></div>
        )}
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
              <Link href="/dashboard" className="text-slate-300 hover:text-emerald-400 transition">
                Dashboard
              </Link>
              <Link href="/results" className="text-slate-300 hover:text-emerald-400 transition">
                Results
              </Link>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="text-center mb-12">
          <h1 className="text-3xl font-bold text-white mb-4">Cast Your Vote</h1>
          <p className="text-slate-400">Select your preferred candidate below. Your vote is secure and anonymous.</p>
        </div>

        {success ? (
          <div className="bg-emerald-500/10 border border-emerald-500/50 rounded-2xl p-8 text-center animate-fadeIn">
            <div className="text-6xl mb-4">🎉</div>
            <h2 className="text-2xl font-bold text-emerald-400 mb-2">Vote Cast Successfully!</h2>
            <p className="text-slate-400 mb-6">Your vote has been recorded on the blockchain.</p>
            <Link href="/results" className="bg-emerald-600 hover:bg-emerald-700 text-white px-6 py-3 rounded-lg transition">
              View Results
            </Link>
          </div>
        ) : (
          <>
            {error && (
              <div className="bg-red-500/10 border border-red-500/50 text-red-400 px-4 py-3 rounded-lg mb-6">
                {error}
              </div>
            )}

            {/* Candidates Grid */}
            <div className="grid md:grid-cols-3 gap-6 mb-8">
              {candidates.map((candidate) => (
                <button
                  key={candidate.id}
                  onClick={() => setSelectedCandidate(candidate.id)}
                  className={`bg-slate-800/50 border-2 rounded-2xl p-6 text-left transition ${
                    selectedCandidate === candidate.id
                      ? 'border-emerald-500 bg-emerald-500/10'
                      : 'border-slate-700 hover:border-slate-600'
                  }`}
                >
                  <div className="w-16 h-16 bg-gradient-to-br from-emerald-500 to-cyan-500 rounded-full mb-4 flex items-center justify-center text-3xl">
                    {candidate.id === 'candidate_a' ? '🔵' : candidate.id === 'candidate_b' ? '🔴' : '🟢'}
                  </div>
                  <h3 className="text-xl font-bold text-white mb-1">{candidate.name}</h3>
                  <p className="text-emerald-400 text-sm mb-3">{candidate.party}</p>
                  <p className="text-slate-400 text-sm">{candidate.description}</p>
                  
                  {selectedCandidate === candidate.id && (
                    <div className="mt-4 flex items-center text-emerald-400">
                      <svg className="w-5 h-5 mr-1" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                      </svg>
                      Selected
                    </div>
                  )}
                </button>
              ))}
            </div>

            {/* Vote Button */}
            <div className="text-center">
              <button
                onClick={handleVote}
                disabled={!selectedCandidate || loading}
                className="bg-emerald-600 hover:bg-emerald-700 disabled:bg-slate-700 disabled:cursor-not-allowed text-white font-bold py-4 px-12 rounded-xl transition transform hover:scale-105 disabled:transform-none flex items-center mx-auto"
              >
                {loading ? (
                  <>
                    <div className="animate-spin rounded-full h-5 w-5 border-t-2 border-b-2 border-white mr-2"></div>
                    Processing...
                  </>
                ) : (
                  <>
                    <svg className="w-6 h-6 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    Cast Vote
                  </>
                )}
              </button>
              <p className="text-slate-500 text-sm mt-4">
                🔒 Your vote will be securely recorded on the blockchain
              </p>
            </div>
          </>
        )}
      </main>
    </div>
  );
}
