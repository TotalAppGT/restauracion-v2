import { useState } from 'react';
import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';

export default function Layout() {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div style={{ display: 'flex', minHeight: '100vh' }}>
      <Sidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} />
      <div className="main-content">
        <button className="btn btn-in btn-sm" 
                style={{ marginBottom: 16, display: typeof window !== 'undefined' && window.innerWidth <= 768 ? 'block' : 'none' }}
                onClick={() => setSidebarOpen(true)}>
          <i className="fas fa-bars" /> Menú
        </button>
        <Outlet />
      </div>
      <div id="toast-container" className="toast-container" />
    </div>
  );
}