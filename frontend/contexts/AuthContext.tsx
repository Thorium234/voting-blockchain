'use client';

import { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import axios from 'axios';
import { jwtDecode } from 'jwt-decode';
import { API_ENDPOINTS } from '@/lib/api';

interface User {
  id: number;
  email: string;
  voter_id: string;
  has_voted: boolean;
  is_admin: boolean;
  created_at: string;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string, deviceFingerprint?: string) => Promise<void>;
  register: (email: string, voterId: string, password: string) => Promise<void>;
  logout: () => void;
  refreshAccessToken: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [refreshToken, setRefreshToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // Check for existing tokens on mount
    const storedToken = localStorage.getItem('access_token');
    const storedRefreshToken = localStorage.getItem('refresh_token');
    
    if (storedToken && storedRefreshToken) {
      setToken(storedToken);
      setRefreshToken(storedRefreshToken);
      fetchUser(storedToken);
    } else {
      setIsLoading(false);
    }
  }, []);

  const fetchUser = async (accessToken: string) => {
    try {
      const response = await axios.get(API_ENDPOINTS.ME, {
        headers: { Authorization: `Bearer ${accessToken}` }
      });
      setUser(response.data);
    } catch (error) {
      // Token expired, try to refresh
      const storedRefreshToken = localStorage.getItem('refresh_token');
      if (storedRefreshToken) {
        await refreshAccessToken();
      } else {
        logout();
      }
    } finally {
      setIsLoading(false);
    }
  };

  const refreshAccessToken = async ()  => {
    const storedRefreshToken = localStorage.getItem('refresh_token');
    if (!storedRefreshToken) {
      logout();
      return;
    }

    try {
      const response = await axios.post(API_ENDPOINTS.REFRESH, {
        refresh_token: storedRefreshToken
      });
      
      const { access_token, refresh_token } = response.data;
      localStorage.setItem('access_token', access_token);
      localStorage.setItem('refresh_token', refresh_token);
      setToken(access_token);
      setRefreshToken(refresh_token);
      
      await fetchUser(access_token);
    } catch (error) {
      logout();
    }
  };

  const login = async (email: string, password: string, deviceFingerprint?: string) => {
    const response = await axios.post(API_ENDPOINTS.LOGIN, {
      email,
      password,
      device_fingerprint: deviceFingerprint
    });

    const { access_token, refresh_token } = response.data;
    localStorage.setItem('access_token', access_token);
    localStorage.setItem('refresh_token', refresh_token);
    setToken(access_token);
    setRefreshToken(refresh_token);

    await fetchUser(access_token);
  };

  const register = async (email: string, voterId: string, password: string) => {
    await axios.post(API_ENDPOINTS.REGISTER, {
      email,
      voter_id: voterId,
      password
    });
  };

  const logout = () => {
    if (token) {
      axios.post(API_ENDPOINTS.LOGOUT, {}, {
        headers: { Authorization: `Bearer ${token}` }
      }).catch(() => {});
    }
    
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    setToken(null);
    setRefreshToken(null);
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{
      user,
      token,
      refreshToken,
      isAuthenticated: !!user,
      isLoading,
      login,
      register,
      logout,
      refreshAccessToken
    }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
