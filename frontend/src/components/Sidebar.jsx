import { useState } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { logout } from '../utils/api';

const ALL_MENU = [
  { id: 'dashboard', label: 'Dashboard General', icon: 'fas fa-tachometer-alt', section: 'PRINCIPAL' },
  { id: 'reportes', label: 'Reporte de Grupos', icon: 'fas fa-file-alt', section: 'REPORTES' },
  { id: 'reporteDigital', label: 'Reporte Digital', icon: 'fas fa-mobile-alt', section: 'REPORTES' },
  { id: 'generador', label: 'Generador Reportes', icon: 'fas fa-file-invoice', section: 'REPORTES' },
  { id: 'hermanos', label: 'Hermanos Lideres', icon: 'fas fa-user-tie', section: 'GESTION' },
  { id: 'supervisores', label: 'Supervisores', icon: 'fas fa-user-shield', section: 'GESTION' },
  { id: 'pastores', label: 'Pastores', icon: 'fas fa-church', section: 'GESTION' },
  { id: 'ayudapastor', label: 'Ayuda Pastor', icon: 'fas fa-hands-helping', section: 'GESTION' },
  { id: 'seguimientos', label: 'Seguimientos', icon: 'fas fa-user-check', section: 'GESTION' },
  { id: 'bautizos', label: 'Bautizos', icon: 'fas fa-water', section: 'GESTION' },
  { id: 'membresia', label: 'Membresia', icon: 'fas fa-id-card', section: 'GESTION' },
  { id: 'ministerios', label: 'Ministerios', icon: 'fas fa-users-cog', section: 'GESTION' },
  { id: 'diezmos', label: 'Diezmos', icon: 'fas fa-coins', section: 'FINANZAS' },
  { id: 'gastos', label: 'Gastos', icon: 'fas fa-receipt', section: 'FINANZAS' },
  { id: 'cuadre', label: 'Cuadre Dominical', icon: 'fas fa-calculator', section: 'FINANZAS' },
  { id: 'cultos', label: 'Asistencia Cultos', icon: 'fas fa-users', section: 'FINANZAS' },
  { id: 'inventario', label: 'Inventario', icon: 'fas fa-boxes', section: 'RECURSOS' },
  { id: 'insumos', label: 'Insumos', icon: 'fas fa-spray-can', section: 'RECURSOS' },
  { id: 'envio', label: 'Centro de Envios', icon: 'fas fa-paper-plane', section: 'COMUNICACION' },
  { id: 'notificaciones', label: 'Notificaciones', icon: 'fas fa-bell', section: 'COMUNICACION' },
  { id: 'contactos', label: 'Contactos', icon: 'fas fa-address-book', section: 'COMUNICACION' },
  { id: 'usuarios', label: 'Usuarios', icon: 'fas fa-user-cog', section: 'ADMIN' },
  { id: 'bitacora', label: 'Bitacora', icon: 'fas fa-clipboard-list', section: 'ADMIN' },
  { id: 'configuracion', label: 'Configuracion', icon: 'fas fa-cog', section: 'ADMIN' },
];

export default function Sidebar({ open, onClose }) {
  const { user, hasModule } = useAuth();
  const navigate = useNavigate();

  function handleNav(id) {
    navigate(id === 'dashboard' ? '/' : `/${id}`);
    if (onClose) onClose();
  }

  const visibleMenu = ALL_MENU.filter(m => m.id === 'dashboard' || m.id === 'configuracion' || hasModule(m.id));

  let currentSection = '';
  return (
    <aside className={`sidebar ${open ? 'open' : ''}`}>
      <div className="sidebar-logo">
        <img src="/logo.png" alt="Logo" onError={e => e.target.style.display = 'none'} />
        <div style={{ fontSize: 16, fontWeight: 900, marginTop: 8 }}>
          {user?.nombre || 'REDIL'}
        </div>
        <div style={{ fontSize: 10, opacity: .6, marginTop: 2 }}>{user?.rol || ''}</div>
      </div>
      <nav className="sidebar-nav">
        {visibleMenu.map(m => {
          const showSection = m.section !== currentSection;
          currentSection = m.section;
          return (
            <div key={m.id}>
              {showSection && <div className="sidebar-section">{m.section}</div>}
              <div className="sidebar-item" onClick={() => handleNav(m.id)}>
                <i className={m.icon} />
                <span>{m.label}</span>
              </div>
            </div>
          );
        })}
      </nav>
    </aside>
  );
}