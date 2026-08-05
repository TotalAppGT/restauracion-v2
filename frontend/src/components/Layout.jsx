import { useState } from 'react';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import Sidebar from './Sidebar';

const TITLES = {
  dashboard: 'Dashboard General',
  reportes: 'Reporte de Grupos',
  reporteDigital: 'Reporte Digital',
  generador: 'Generador de Reportes',
  hermanos: 'Hermanos Líderes',
  supervisores: 'Supervisores',
  pastores: 'Pastores de Zona',
  ayudapastor: 'Ayuda de Pastor',
  seguimientos: 'Seguimientos',
  bautizos: 'Bautizos en Agua',
  diezmos: 'Control de Diezmos',
  gastos: 'Control de Gastos',
  cuadre: 'Cuadre Dominical',
  inventario: 'Inventario',
  insumos: 'Insumos',
  envio: 'Centro de Envíos',
  notificaciones: 'Notificaciones Automáticas',
  contactos: 'Tabla de Contactos',
  usuarios: 'Usuarios',
  bitacora: 'Bitácora de Accesos',
  configuracion: 'Configuración',
};

export default function Layout() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();
  const currentPath = location.pathname === '/' ? 'dashboard' : location.pathname.replace('/', '');
  const title = TITLES[currentPath] || 'REDIL';

  return (
    <div className="app-shell">
      <Sidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} />
      <div className="main">
        <header className="topbar">
          <button className="menu-btn" onClick={() => setSidebarOpen(true)}><i className="fas fa-bars" /></button>
          <div className="tb-title">{title}</div>
          <div className="tb-right">
            <button className="tb-btn" onClick={() => navigate('/')} title="Inicio"><i className="fas fa-home" /></button>
            <div className="user-pill"><i className="fas fa-user-circle" /><span>Admin</span></div>
          </div>
        </header>
        <div className="content">
          <Outlet />
        </div>
      </div>
      <div id="toastWrap" />
    </div>
  );
}