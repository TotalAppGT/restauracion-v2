import { useState, useEffect } from 'react';
import { dispatch } from '../utils/api';
import { useAuth } from '../context/AuthContext';

export default function Dashboard() {
  const { user } = useAuth();
  const [data, setData] = useState(null);

  useEffect(() => { dispatch('getDashboard').then(d => { if (d && d.lideres !== undefined) setData(d); }); }, []);

  if (!data) return <div className="content" style={{ padding: 40, textAlign: 'center' }}><div className="g-spinner" style={{ margin: '0 auto' }} /><p style={{ marginTop: 12, fontWeight: 700, color: 'var(--pr)' }}>Cargando dashboard...</p></div>;

  return (
    <div>
      {/* Welcome Banner */}
      <div className="welcome-banner">
        <div>
          <h1>Bienvenido, {user?.nombre}</h1>
          <p>{new Date().toLocaleDateString('es-GT', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}</p>
        </div>
        <div style={{ fontSize: 40, opacity: .3 }}>⛪</div>
      </div>

      {/* KPI Stats */}
      <div className="sg">
        <div className="sc"><div className="sc-ico"><i className="fas fa-user-tie" /></div><div className="sc-v">{data.lideres || 0}</div><div className="sc-l">Líderes</div></div>
        <div className="sc g"><div className="sc-ico"><i className="fas fa-file-alt" /></div><div className="sc-v">{data.reportesMes || 0}</div><div className="sc-l">Reportes Mes</div></div>
        <div className="sc i"><div className="sc-ico"><i className="fas fa-users" /></div><div className="sc-v">{data.asistencia || 0}</div><div className="sc-l">Asistencia</div></div>
        <div className="sc o"><div className="sc-ico"><i className="fas fa-coins" /></div><div className="sc-v">Q{(data.ofTotal || 0).toLocaleString()}</div><div className="sc-l">Ofrenda Total</div></div>
        <div className="sc p"><div className="sc-ico"><i className="fas fa-user-check" /></div><div className="sc-v">{data.segTotal || 0}</div><div className="sc-l">Seguimientos</div></div>
        <div className="sc r"><div className="sc-ico"><i className="fas fa-clock" /></div><div className="sc-v">{data.pendientes || 0}</div><div className="sc-l">Pendientes</div></div>
      </div>

      {/* Summary Cards */}
      <div className="dg">
        <div className="card">
          <div className="ct"><i className="fas fa-chart-bar" /> Resumen General</div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, fontSize: 13 }}>
            <div><strong>Grupos realizados:</strong> {data.gruposRealizados || 0}</div>
            <div><strong>Meta de grupos:</strong> {data.metaGrupos || 407}</div>
            <div><strong>Convertidos:</strong> {data.convertidos || 0}</div>
            <div><strong>Reconciliados:</strong> {data.reconciliados || 0}</div>
          </div>
        </div>
        <div className="card">
          <div className="ct"><i className="fas fa-info-circle" /> Información</div>
          <div style={{ fontSize: 13 }}>
            <p style={{ color: 'var(--tx2)', lineHeight: 1.8 }}>
              <i className="fas fa-check-circle" style={{ color: 'var(--ok)' }} /> Sistema operativo correctamente.<br />
              <i className="fas fa-database" style={{ color: 'var(--inf)' }} /> {data.reportesMes || 0} reportes registrados este mes.<br />
              <i className="fas fa-bell" style={{ color: 'var(--ac)' }} /> {data.pendientes || 0} ofrendas pendientes de recibir.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}