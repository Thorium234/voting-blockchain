'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/contexts/AuthContext';
import axios from 'axios';
import { Pie, Line, Bar } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  ArcElement,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend
} from 'chart.js';

ChartJS.register(
  ArcElement,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend
);

export default function CommandCenterPage() {
  const { user, isAuthenticated, isLoading, token } = useAuth();
  const router = useRouter();
  const [analytics, setAnalytics] = useState<any>(null);
  const [health, setHealth] = useState<any>(null);
  const [surveillance, setSurveillance] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!isLoading && (!isAuthenticated || user?.role !== 'superadmin')) {
      router.push('/');
    }
  }, [isLoading, isAuthenticated, user, router]);

  useEffect(() => {
    if (token && user?.role === 'superadmin') {
      fetchData();
      const interval = setInterval(fetchData, 30000); // Refresh every 30s
      return () => clearInterval(interval);
    }
  }, [token, user]);

  const fetchData = async () => {
    if (!token) return;
    try {
      const [analyticsRes, healthRes, surveillanceRes] = await Promise.all([
        axios.get('http://localhost:8000/api/v1/command-center/analytics/comprehensive', {
          headers: { Authorization: `Bearer ${token}` }
        }),
        axios.get('http://localhost:8000/api/v1/command-center/system/health-check', {
          headers: { Authorization: `Bearer ${token}` }
        }),
        axios.get('http://localhost:8000/api/v1/command-center/surveillance/admin-activity?hours=24', {
          headers: { Authorization: `Bearer ${token}` }
        })
      ]);
      setAnalytics(analyticsRes.data);
      setHealth(healthRes.data);
      setSurveillance(surveillanceRes.data);
    } catch (error) {
      console.error('Error fetching data:', error);
    } finally {
      setLoading(false);
    }
  };

  const downloadReport = async () => {
    if (!token) return;
    try {
      const response = await axios.get('http://localhost:8000/api/v1/command-center/reports/summary?election_id=ELEC_XXX', {
        headers: { Authorization: `Bearer ${token}` }
      });
      const blob = new Blob([JSON.stringify(response.data, null, 2)], { type: 'application/json' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `election-report-${new Date().toISOString()}.json`;
      a.click();
    } catch (error) {
      console.error('Error downloading report:', error);
    }
  };

  if (isLoading || loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-emerald-500"></div>
      </div>
    );
  }

  // Chart data
  const locationTurnoutData = analytics?.location_turnout ? {
    labels: analytics.location_turnout.map((l: any) => l.location),
    datasets: [{
      label: 'Voter Turnout %',
      data: analytics.location_turnout.map((l: any) => l.percentage),
      backgroundColor: [
        'rgba(16, 185, 129, 0.8)',
        'rgba(59, 130, 246, 0.8)',
        'rgba(239, 68, 68, 0.8)',
        'rgba(245, 158, 11, 0.8)',
        'rgba(139, 92, 246, 0.8)',
      ],
    }]
  } : null;

  const hourlyTrendsData = analytics?.hourly_trends ? {
    labels: analytics.hourly_trends.map((h: any) => `${h.hour}:00`),
    datasets: [{
      label: 'Votes per Hour',
      data: analytics.hourly_trends.map((h: any) => h.votes),
      borderColor: 'rgb(16, 185, 129)',
      backgroundColor: 'rgba(16, 185, 129, 0.1)',
      tension: 0.4
    }]
  } : null;

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-emerald-900">
      <header className="bg-slate-900/80 backdrop-blur-md border-b border-slate-700">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 bg-gradient-to-br from-emerald-500 to-emerald-600 rounded-lg flex items-center justify-center">
                <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
              </div>
              <div>
                <h1 className="text-xl font-bold text-white">Command Center</h1>
                <p className="text-xs text-slate-400">Super Admin Dashboard</p>
              </div>
            </div>
            <div className="flex items-center space-x-4">
              <Link href="/admin" className="text-slate-300 hover:text-emerald-400 transition">Admin Panel</Link>
              <button onClick={downloadReport} className="bg-emerald-600 hover:bg-emerald-700 text-white px-4 py-2 rounded-lg transition text-sm">
                Download Report
              </button>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* System Health */}
        {health && (
          <div className="grid grid-cols-4 gap-4 mb-8">
            <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-4">
              <div className="text-2xl font-bold text-emerald-400">{health.database.total_voters}</div>
              <div className="text-slate-400 text-sm">Total Voters</div>
            </div>
            <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-4">
              <div className="text-2xl font-bold text-emerald-400">{health.blockchain.total_votes}</div>
              <div className="text-slate-400 text-sm">Total Votes</div>
            </div>
            <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-4">
              <div className="text-2xl font-bold text-emerald-400">{health.elections.active}</div>
              <div className="text-slate-400 text-sm">Active Elections</div>
            </div>
            <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-4">
              <div className="flex items-center space-x-2">
                <div className={`w-3 h-3 rounded-full ${health.blockchain.is_valid ? 'bg-emerald-500' : 'bg-red-500'}`}></div>
                <div className="text-slate-400 text-sm">Blockchain {health.blockchain.is_valid ? 'Valid' : 'Invalid'}</div>
              </div>
            </div>
          </div>
        )}

        {/* Charts */}
        <div className="grid grid-cols-2 gap-6 mb-8">
          {/* Location Turnout */}
          {locationTurnoutData && (
            <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6">
              <h3 className="text-lg font-semibold text-white mb-4">Voter Turnout by Location</h3>
              <Pie data={locationTurnoutData} options={{ maintainAspectRatio: true }} />
            </div>
          )}

          {/* Hourly Trends */}
          {hourlyTrendsData && (
            <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6">
              <h3 className="text-lg font-semibold text-white mb-4">Voting Trends (24h)</h3>
              <Line data={hourlyTrendsData} options={{ maintainAspectRatio: true, scales: { y: { beginAtZero: true } } }} />
            </div>
          )}
        </div>

        {/* Location Breakdown Table */}
        {analytics?.location_turnout && (
          <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6 mb-8">
            <h3 className="text-lg font-semibold text-white mb-4">Location Breakdown</h3>
            <table className="w-full">
              <thead className="bg-slate-900/50">
                <tr>
                  <th className="px-4 py-2 text-left text-slate-400 text-sm">Location</th>
                  <th className="px-4 py-2 text-left text-slate-400 text-sm">Total Voters</th>
                  <th className="px-4 py-2 text-left text-slate-400 text-sm">Voted</th>
                  <th className="px-4 py-2 text-left text-slate-400 text-sm">Turnout %</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-700">
                {analytics.location_turnout.map((loc: any, idx: number) => (
                  <tr key={idx} className="hover:bg-slate-700/30">
                    <td className="px-4 py-3 text-white">{loc.location}</td>
                    <td className="px-4 py-3 text-white">{loc.total_voters}</td>
                    <td className="px-4 py-3 text-white">{loc.voted}</td>
                    <td className="px-4 py-3">
                      <span className="text-emerald-400 font-semibold">{loc.percentage}%</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Admin Surveillance */}
        {surveillance && (
          <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6">
            <h3 className="text-lg font-semibold text-white mb-4">Admin Surveillance (24h)</h3>
            <div className="space-y-3">
              {surveillance.admins?.map((admin: any, idx: number) => (
                <div key={idx} className="bg-slate-900/50 border border-slate-600 rounded-lg p-4">
                  <div className="flex justify-between items-start">
                    <div>
                      <div className="flex items-center space-x-2">
                        <span className="text-white font-semibold">{admin.email}</span>
                        <span className={`px-2 py-1 rounded text-xs ${admin.is_online ? 'bg-emerald-500/20 text-emerald-400' : 'bg-slate-600 text-slate-300'}`}>
                          {admin.is_online ? 'Online' : 'Offline'}
                        </span>
                        <span className="px-2 py-1 rounded text-xs bg-purple-500/20 text-purple-400">{admin.role}</span>
                      </div>
                      <div className="text-slate-400 text-sm mt-1">
                        Last active: {admin.last_activity ? new Date(admin.last_activity).toLocaleString() : 'Never'}
                      </div>
                      {admin.session_ip && (
                        <div className="text-slate-500 text-xs mt-1">IP: {admin.session_ip}</div>
                      )}
                    </div>
                    <div className="text-right">
                      <div className="text-emerald-400 font-bold text-lg">{admin.action_count_24h}</div>
                      <div className="text-slate-400 text-xs">Actions</div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
