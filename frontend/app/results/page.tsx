'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import axios from 'axios';
import { API_ENDPOINTS } from '@/lib/api';

interface VoteResult {
  candidate_id: string;
  vote_count: number;
  percentage: number;
}

interface BlockchainBlock {
  index: number;
  timestamp: string;
  votes_count: number;
  previous_hash: string;
  nonce: number;
  hash: string;
}

export default function ResultsPage() {
  const [results, setResults] = useState<VoteResult[]>([]);
  const [totalVotes, setTotalVotes] = useState(0);
  const [blockchainHeight, setBlockchainHeight] = useState(0);
  const [loading, setLoading] = useState(true);
  const [showBlockchain, setShowBlockchain] = useState(false);
  const [blocks, setBlocks] = useState<BlockchainBlock[]>([]);

  useEffect(() => {
    fetchResults();
  }, []);

  const fetchResults = async () => {
    try {
      const response = await axios.get(API_ENDPOINTS.RESULTS);
      setResults(response.data.results);
      setTotalVotes(response.data.total_votes);
      setBlockchainHeight(response.data.blockchain_height);
    } catch (error) {
      console.error('Error fetching results:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchBlockchain = async () => {
    try {
      const response = await axios.get(API_ENDPOINTS.BLOCKCHAIN);
      setBlocks(response.data.blocks);
      setShowBlockchain(true);
    } catch (error) {
      console.error('Error fetching blockchain:', error);
    }
  };

  const getCandidateColor = (id: string) => {
    const colors: Record<string, string> = {
      candidate_a: 'from-blue-500 to-blue-600',
      candidate_b: 'from-red-500 to-red-600',
      candidate_c: 'from-green-500 to-green-600',
    };
    return colors[id] || 'from-gray-500 to-gray-600';
  };

  const getCandidateEmoji = (id: string) => {
    const emojis: Record<string, string> = {
      candidate_a: '🔵',
      candidate_b: '🔴',
      candidate_c: '🟢',
    };
    return emojis[id] || '🗳️';
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-emerald-500"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen">
      {/* Header */}
      <header className="bg-slate-900/80 backdrop-blur-md border-b border-slate-700">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <Link href="/" className="flex items-center space-x-2">
              <div className="w-8 h-8 bg-emerald-500 rounded-lg flex items-center justify-center">
                <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                </svg>
              </div>
              <span className="text-xl font-bold text-white">BlockchainVote</span>
            </Link>
            
            <nav className="flex items-center space-x-4">
              <Link href="/" className="text-slate-300 hover:text-emerald-400 transition">Home</Link>
              <Link href="/login" className="text-slate-300 hover:text-emerald-400 transition">Login</Link>
            </nav>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold text-white mb-4">Voting Results</h1>
          <p className="text-slate-400">Live results from the blockchain</p>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-3 gap-4 mb-12">
          <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6 text-center">
            <div className="text-3xl font-bold text-emerald-400">{totalVotes}</div>
            <div className="text-slate-400 text-sm">Total Votes</div>
          </div>
          <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6 text-center">
            <div className="text-3xl font-bold text-emerald-400">{results.length}</div>
            <div className="text-slate-400 text-sm">Candidates</div>
          </div>
          <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6 text-center">
            <div className="text-3xl font-bold text-emerald-400">{blockchainHeight}</div>
            <div className="text-slate-400 text-sm">Blockchain Height</div>
          </div>
        </div>

        {/* Results Chart */}
        <div className="space-y-6 mb-12">
          {results.map((result) => (
            <div key={result.candidate_id} className="bg-slate-800/50 border border-slate-700 rounded-xl p-6">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center space-x-4">
                  <div className={`w-12 h-12 rounded-full bg-gradient-to-br ${getCandidateColor(result.candidate_id)} flex items-center justify-center text-2xl`}>
                    {getCandidateEmoji(result.candidate_id)}
                  </div>
                  <div>
                    <h3 className="text-xl font-semibold text-white capitalize">{result.candidate_id.replace('_', ' ')}</h3>
                    <p className="text-slate-400">{result.vote_count} votes</p>
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-2xl font-bold text-emerald-400">{result.percentage}%</div>
                </div>
              </div>
              <div className="w-full bg-slate-700 rounded-full h-4">
                <div 
                  className={`bg-gradient-to-r ${getCandidateColor(result.candidate_id)} h-4 rounded-full transition-all duration-500`}
                  style={{ width: `${result.percentage}%` }}
                ></div>
              </div>
            </div>
          ))}
        </div>

        {results.length === 0 && (
          <div className="text-center py-12">
            <div className="text-6xl mb-4">🗳️</div>
            <h2 className="text-xl font-semibold text-white mb-2">No Votes Yet</h2>
            <p className="text-slate-400 mb-6">Be the first to cast your vote!</p>
            <Link href="/register" className="bg-emerald-600 hover:bg-emerald-700 text-white px-6 py-3 rounded-lg transition">
              Register Now
            </Link>
          </div>
        )}

        {/* Blockchain View Button */}
        <div className="text-center mb-8">
          <button 
            onClick={fetchBlockchain}
            className="bg-slate-700 hover:bg-slate-600 text-white px-6 py-3 rounded-lg transition"
          >
            {showBlockchain ? 'Hide Blockchain' : 'View Blockchain'}
          </button>
        </div>

        {/* Blockchain Display */}
        {showBlockchain && (
          <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6 animate-fadeIn">
            <h2 className="text-xl font-bold text-white mb-6">Blockchain</h2>
            <div className="space-y-4">
              {blocks.map((block, index) => (
                <div key={block.index} className="bg-slate-900/50 border border-slate-600 rounded-lg p-4">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-emerald-400 font-mono">Block #{block.index}</span>
                    <span className="text-slate-500 text-sm">{new Date(block.timestamp).toLocaleString()}</span>
                  </div>
                  <div className="grid grid-cols-2 gap-2 text-sm">
                    <div>
                      <span className="text-slate-500">Votes: </span>
                      <span className="text-white font-mono">{block.votes_count}</span>
                    </div>
                    <div>
                      <span className="text-slate-500">Nonce: </span>
                      <span className="text-white font-mono">{block.nonce}</span>
                    </div>
                  </div>
                  <div className="mt-2">
                    <span className="text-slate-500 text-sm">Hash: </span>
                    <span className="text-white font-mono text-xs">{block.hash}</span>
                  </div>
                  {index > 0 && (
                    <div className="mt-2">
                      <span className="text-slate-500 text-sm">Previous: </span>
                      <span className="text-white font-mono text-xs">{block.previous_hash.substring(0, 32)}...</span>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
