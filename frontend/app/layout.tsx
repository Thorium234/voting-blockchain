import type { Metadata } from 'next';
import { AuthProvider } from '@/contexts/AuthContext';
import './globals.css';

export const metadata: Metadata = {
  title: 'Blockchain Voting System',
  description: 'Secure, tamper-resistant blockchain-based voting system',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="bg-slate-900 text-slate-200">
        <AuthProvider>
          {children}
        </AuthProvider>
      </body>
    </html>
  );
}
