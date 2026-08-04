import { createContext, useContext, useState, useEffect } from 'react';
import { dispatch, getUser } from '../utils/api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [config, setConfig] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const u = getUser();
    if (u) setUser(u);
    loadConfig();
    setLoading(false);
  }, []);

  async function loadConfig() {
    try {
      const res = await dispatch('getConfig');
      if (res && res.ok !== false) setConfig(res);
    } catch (e) {
      console.error('Config load failed');
    }
  }

  const value = {
    user, setUser,
    config, loadConfig,
    loading,
    isAdmin: user?.rol === 'Admin' || user?.isPropietario,
    isPropietario: user?.isPropietario,
    allowedModules: user?.menu || [],
    hasModule: (mod) => !user || user.isPropietario || (user?.menu || []).includes(mod),
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be inside AuthProvider');
  return ctx;
}