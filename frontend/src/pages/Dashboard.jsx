import { useState, useEffect } from 'react';
import { dispatch } from '../utils/api';
import { useAuth } from '../context/AuthContext';

export default function Dashboard() {
  const { user, config } = useAuth();
  const [data, setData] = useState(null);

  useEffect(() => {
    dispatch('getDashboard').then(d => {
      if (d && d.lideres !== undefined) setData(d);
    });
  }, []);

  if (!data) return <div className="empty"><i className="fas fa-circle-notch fa-spin" /><p>Cargando dashboard...</p></div>;

  const sysName = config?.nombre || 'REDIL';
  const kpis = [
    { label: 'Líderes', value: data.lideres, icon: '👥' },
    { label: 'Reportes del Mes', value: data.reportesMes, icon: '📋' },
    { label: 'Asistencia Total', value: data.asistencia, icon: '🙋' },
    { label: 'Ofrenda Total', value: `Q${(data.ofTotal || 0).toLocaleString()}`, icon: '💰' },
    { label: 'Seguimientos', value: data.segTotal, icon: '🤝' },
    { label: 'Pendientes', value: data.pendientes, icon: '⏳' },
  ];

  return (
    <div>
      <div className="card" style={{ background: 'linear-gradient(135deg, var(--pr), var(--pr2))', color: '#fff', border: 'none', marginBottom: 20 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h1 style={{ fontSize: 22, fontWeight: 900 }}>Bienvenido, {user?.nombre}</h1>
            <p style={{ fontSize: 13, opacity: .8, marginTop: 4 }}>{sysName} · {new Date().toLocaleDateString('es-GT', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}</p>
          </div>
          <div style={{ fontSize: 40, opacity: .3 }}>⛪</div>
        </div>
      </div>

      <div className="kpis">
        {kpis.map((k, i) => (
          <div className="kpi" key={i}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <div className="v">{k.value}</div>
              <span style={{ fontSize: 20 }}>{k.icon}</span>
            </div>
            <div className="l">{k.label}</div>
          </div>
        ))}
      </div>

      <div className="card" style={{ marginTop: 20 }}>
        <div className="card-hdr"><h2><i className="fas fa-info-circle" /> Resumen Rápido</h2></div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 12, fontSize: 14 }}>
          <div><strong>Grupos realizados:</strong> {data.gruposRealizados || 0}</div>
          <div><strong>Convertidos:</strong> {data.convertidos || 0}</div>
          <div><strong>Reconciliados:</strong> {data.reconciliados || 0}</div>
          <div><strong>Meta de grupos:</strong> {data.metaGrupos || 407}</div>
        </div>
      </div>
    </div>
  );
}