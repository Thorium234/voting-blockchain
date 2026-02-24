'use client';

import Link from 'next/link';
import { useAuth } from '@/contexts/AuthContext';
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';

export default function Home() {
  const { user, isAuthenticated, isLoading, logout } = useAuth();
  const router = useRouter();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  const handleLogout = () => {
    logout();
    router.push('/');
  };

  if (!mounted || isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-900">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-emerald-500"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-900">
      {/* Header */}
      <header className="bg-slate-900/80 backdrop-blur-md border-b border-slate-700 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center space-x-2">
              <div className="w-8 h-8 bg-emerald-500 rounded-lg flex items-center justify-center">
                <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                </svg>
              </div>
              <span className="text-xl font-bold text-white">BlockchainVote</span>
            </div>
            
            <nav className="hidden md:flex items-center space-x-6">
              <Link href="/" className="text-slate-300 hover:text-emerald-400 transition-colors">Home</Link>
              <Link href="/results" className="text-slate-300 hover:text-emerald-400 transition-colors">Results</Link>
              {isAuthenticated ? (
                <>
                  <Link href="/dashboard" className="text-slate-300 hover:text-emerald-400 transition-colors">Dashboard</Link>
                  {user?.is_admin && (
                    <Link href="/admin" className="text-slate-300 hover:text-emerald-400 transition-colors">Admin</Link>
                  )}
                  <button 
                    onClick={handleLogout}
                    className="bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded-lg transition-colors"
                  >
                    Logout
                  </button>
                </>
              ) : (
                <>
                  <Link href="/login" className="text-slate-300 hover:text-emerald-400 transition-colors">Login</Link>
                </>
              )}
            </nav>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <div className="text-center animate-fade-in">
          <h1 className="text-5xl md:text-6xl font-bold text-white mb-6">
            Secure Blockchain
            <span className="block text-emerald-500">Voting System</span>
          </h1>
          <p className="text-xl text-slate-400 max-w-2xl mx-auto mb-10">
            A tamper-resistant, transparent voting system powered by blockchain technology. 
            Your vote is secure, anonymous, and verifiable.
          </p>
          
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            {isAuthenticated ? (
              user?.role === 'voter' ? (
                <Link 
                  href="/vote" 
                  className="bg-emerald-600 hover:bg-emerald-700 text-white text-lg px-8 py-4 rounded-xl transition-all hover:scale-105 shadow-lg shadow-emerald-500/25"
                >
                  Cast Your Vote →
                </Link>
              ) : (
                <Link 
                  href="/admin" 
                  className="bg-purple-600 hover:bg-purple-700 text-white text-lg px-8 py-4 rounded-xl transition-all hover:scale-105 shadow-lg shadow-purple-500/25"
                >
                  Admin Dashboard →
                </Link>
              )
            ) : (
              <>
                <Link 
                  href="/login" 
                  className="bg-emerald-600 hover:bg-emerald-700 text-white text-lg px-8 py-4 rounded-xl transition-all hover:scale-105 shadow-lg shadow-emerald-500/25"
                >
                  🔐 Login to Vote
                </Link>
                <Link 
                  href="/results" 
                  className="bg-slate-700 hover:bg-slate-600 text-white text-lg px-8 py-4 rounded-xl transition-colors"
                >
                  View Results
                </Link>
              </>
            )}
          </div>
          
          {!isAuthenticated && (
            <p className="text-slate-400 text-sm mt-6">
              ℹ️ Contact your administrator to register as a voter
            </p>
          )}
        </div>

        {/* Features Grid */}
        <div className="mt-24 grid md:grid-cols-3 gap-8">
          {[
            {
              icon: '🔗',
              title: 'Blockchain Secured',
              description: 'Every vote is cryptographically secured in a blockchain, making it impossible to alter or delete.'
            },
            {
              icon: '🛡️',
              title: 'Double Vote Prevention',
              description: 'Advanced mechanisms prevent duplicate voting through database and blockchain verification.'
            },
            {
              icon: '📱',
              title: 'Device Binding',
              description: 'Your account is bound to your device for added security. One device, one vote.'
            },
            {
              icon: '⚡',
              title: 'Real-time Results',
              description: 'Vote counts are updated in real-time with full transparency on the blockchain.'
            },
            {
              icon: '🔒',
              title: 'IP Protection',
              description: 'Brute force protection with automatic IP banning keeps the system secure.'
            },
            {
              icon: '👁️',
              title: 'Fully Transparent',
              description: 'Anyone can verify the blockchain integrity and audit all voting activity.'
            }
          ].map((feature, index) => (
            <div 
              key={index}
              className="bg-slate-800/50 backdrop-blur-sm border border-slate-700 rounded-2xl p-6 hover:border-emerald-500/50 transition-all hover:-translate-y-1"
            >
              <div className="text-4xl mb-4">{feature.icon}</div>
              <h3 className="text-xl font-semibold text-white mb-2">{feature.title}</h3>
              <p className="text-slate-400">{feature.description}</p>
            </div>
          ))}
        </div>

        {/* How It Works */}
        <div className="mt-24">
          <h2 className="text-3xl font-bold text-white text-center mb-12">How It Works</h2>
          <div className="grid md:grid-cols-4 gap-6">
            {[
              { step: '1', title: 'Get Registered', desc: 'Admin registers your account' },
              { step: '2', title: 'Login', desc: 'Authenticate with credentials' },
              { step: '3', title: 'Vote', desc: 'Cast your vote securely' },
              { step: '4', title: 'Verify', desc: 'View vote on blockchain' }
            ].map((item, index) => (
              <div key={index} className="text-center">
                <div className="w-12 h-12 bg-emerald-600 rounded-full flex items-center justify-center text-xl font-bold text-white mx-auto mb-4">
                  {item.step}
                </div>
                <h3 className="text-lg font-semibold text-white mb-2">{item.title}</h3>
                <p className="text-slate-400 text-sm">{item.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="bg-slate-900 border-t border-slate-800 mt-16 py-8">
        <div className="max-w-7xl mx-auto px-4 text-center text-slate-400">
          <p>© 2026 Blockchain Voting System. All rights reserved.</p>
        </div>
      </footer>
    </div>
  );
}
