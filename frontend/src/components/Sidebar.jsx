import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { logout } from '../utils/api';

const ALL_MENU = [
  { id: 'dashboard', label: 'Dashboard General', icon: 'fas fa-tachometer-alt', section: 'PRINCIPAL' },
  { id: 'reportes', label: 'Reporte de Grupos', icon: 'fas fa-file-alt', section: 'REPORTES' },
  { id: 'reporteDigital', label: 'Reporte Digital', icon: 'fas fa-mobile-alt', section: 'REPORTES' },
  { id: 'generador', label: 'Generador Reportes', icon: 'fas fa-file-invoice', section: 'REPORTES' },
  { id: 'hermanos', label: 'Hermanos Líderes', icon: 'fas fa-user-tie', section: 'GESTIÓN' },
  { id: 'supervisores', label: 'Supervisores', icon: 'fas fa-user-shield', section: 'GESTIÓN' },
  { id: 'pastores', label: 'Pastores de Zona', icon: 'fas fa-church', section: 'GESTIÓN' },
  { id: 'ayudapastor', label: 'Ayuda de Pastor', icon: 'fas fa-hands-helping', section: 'GESTIÓN' },
  { id: 'seguimientos', label: 'Seguimientos', icon: 'fas fa-user-check', section: 'GESTIÓN' },
  { id: 'bautizos', label: 'Bautizos en Agua', icon: 'fas fa-water', section: 'GESTIÓN' },
  { id: 'diezmos', label: 'Control Diezmos', icon: 'fas fa-coins', section: 'FINANZAS' },
  { id: 'gastos', label: 'Control de Gastos', icon: 'fas fa-receipt', section: 'FINANZAS' },
  { id: 'cuadre', label: 'Cuadre Dominical', icon: 'fas fa-calculator', section: 'FINANZAS' },
  { id: 'inventario', label: 'Inventario', icon: 'fas fa-boxes', section: 'RECURSOS' },
  { id: 'insumos', label: 'Insumos', icon: 'fas fa-spray-can', section: 'RECURSOS' },
  { id: 'envio', label: 'Centro de Envíos', icon: 'fas fa-paper-plane', section: 'COMUNICACIÓN' },
  { id: 'notificaciones', label: 'Notificaciones', icon: 'fas fa-bell', section: 'COMUNICACIÓN' },
  { id: 'contactos', label: 'Tabla de Contactos', icon: 'fas fa-address-book', section: 'COMUNICACIÓN' },
  { id: 'usuarios', label: 'Usuarios', icon: 'fas fa-user-cog', section: 'ADMIN' },
  { id: 'bitacora', label: 'Bitácora', icon: 'fas fa-clipboard-list', section: 'ADMIN' },
  { id: 'configuracion', label: 'Configuración', icon: 'fas fa-cog', section: 'ADMIN' },
];

export default function Sidebar({ open, onClose }) {
  const { user, hasModule } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const currentPath = location.pathname === '/' ? 'dashboard' : location.pathname.replace('/', '');

  function handleNav(id) {
    navigate(id === 'dashboard' ? '/' : `/${id}`);
    if (onClose) onClose();
  }

  const visible = ALL_MENU.filter(m => m.id === 'dashboard' || m.id === 'configuracion' || hasModule(m.id));

  let lastSection = '';
  return (
    <>
      <aside className={`sidebar ${open ? 'open' : ''}`}>
        <div className="sb-head">
          <div className="sb-brand">
            <div className="sb-logo-wrap"><i className="fas fa-church" /></div>
            <div><div className="sb-title">Iglesia Restauración</div></div>
          </div>
          <button className="sb-close" onClick={onClose}><i className="fas fa-times" /></button>
        </div>
        <div className="sb-user">
          <div className="sb-avatar"><i className="fas fa-user-circle" /></div>
          <div className="sb-uinfo"><span>{user?.nombre || 'Usuario'}</span><small>{user?.rol || ''}</small></div>
        </div>
        <nav className="sb-nav">
          {visible.map(m => {
            const showSection = m.section !== lastSection;
            lastSection = m.section;
            return (
              <div key={m.id}>
                {showSection && <div className="nl">{m.section}</div>}
                <div className={`ni ${currentPath === m.id ? 'active' : ''}`} onClick={() => handleNav(m.id)}>
                  <i className={m.icon} />
                  <span>{m.label}</span>
                </div>
              </div>
            );
          })}
        </nav>
        <button className="btn-logout" onClick={logout}><i className="fas fa-sign-out-alt" /> Cerrar Sesión</button>
      </aside>
      <div className={`sb-ov ${open ? 'open' : ''}`} onClick={onClose} />
    </>
  );
}