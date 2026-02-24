'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';

export default function NotFound() {
  const router = useRouter();

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      <div className="text-center px-4">
        <div className="mb-8">
          <div className="text-9xl font-bold text-emerald-500 mb-4">404</div>
          <div className="text-6xl mb-4">🔍</div>
        </div>
        
        <h1 className="text-4xl font-bold text-white mb-4">Page Not Found</h1>
        <p className="text-xl text-slate-400 mb-8 max-w-md mx-auto">
          The page you're looking for doesn't exist or has been moved.
        </p>
        
        <div className="flex flex-col sm:flex-row gap-4 justify-center">
          <button
            onClick={() => router.back()}
            className="bg-slate-700 hover:bg-slate-600 text-white px-8 py-3 rounded-xl transition"
          >
            ← Go Back
          </button>
          <Link
            href="/"
            className="bg-emerald-600 hover:bg-emerald-700 text-white px-8 py-3 rounded-xl transition"
          >
            🏠 Home
          </Link>
        </div>
        
        <div className="mt-12 text-slate-500 text-sm">
          <p>Need help? Contact your administrator</p>
        </div>
      </div>
    </div>
  );
}
