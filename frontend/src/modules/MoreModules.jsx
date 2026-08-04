import { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { dispatch, toast } from '../utils/api';
import CrudModule from './index';

// ====== INVENTARIO ======
export function InventarioPage() {
  return <CrudModule
    title="Inventario" icon="fas fa-boxes" getAction="getInventario" saveAction="saveInventario" deleteAction="deleteInventario"
    columns={[{label:'Artículo',field:'Articulo'},{label:'Categoría',field:'Categoria'},{label:'Cantidad',field:'Cantidad'},{label:'Estado',field:'Estado'}]}
    fields={[{label:'Artículo',field:'Articulo',required:true},{label:'Categoría',field:'Categoria'},{label:'Cantidad',field:'Cantidad',type:'number'},{label:'Unidad',field:'Unidad'},{label:'Estado',field:'Estado',type:'select',options:['Bueno','Regular','Malo']},{label:'Ubicación',field:'Ubicacion'},{label:'Valor Q',field:'ValorQ',type:'number'}]}
  />;
}

// ====== INSUMOS ======
export function InsumosPage() {
  return <CrudModule
    title="Insumos" icon="fas fa-spray-can" getAction="getInsumos" saveAction="saveInsumo" deleteAction="deleteInsumo"
    columns={[{label:'Artículo',field:'Articulo'},{label:'Categoría',field:'Categoria'},{label:'Cantidad',field:'Cantidad'},{label:'Stock Mín',field:'StockMinimo'}]}
    fields={[{label:'Artículo',field:'Articulo',required:true},{label:'Categoría',field:'Categoria'},{label:'Cantidad',field:'Cantidad',type:'number'},{label:'Unidad',field:'Unidad'},{label:'Precio Unit Q',field:'PrecioUnitarioQ',type:'number'},{label:'Stock Mínimo',field:'StockMinimo',type:'number'},{label:'Proveedor',field:'Proveedor'}]}
  />;
}

// ====== USUARIOS ======
export function UsuariosPage() {
  return <CrudModule
    title="Usuarios" icon="fas fa-user-cog" getAction="getUsuarios" saveAction="saveUsuario" deleteAction="deleteUsuario"
    columns={[
      {label:'Nombre',field:'Nombre',render:u=><b>{u['Nombre']}</b>},
      {label:'Email',field:'Email'},
      {label:'Rol',field:'Rol',render:u=><span className="bdg bb">{u['Rol']}</span>},
      {label:'Activo',field:'Activo',render:u=><span className={`bdg ${u['Activo']==='SI'?'bg':'bgr'}`}>{u['Activo']}</span>},
    ]}
    fields={[
      {label:'Nombre',field:'Nombre',required:true},
      {label:'Email',field:'Email',required:true,type:'email'},
      {label:'Rol',field:'Rol',type:'select',options:['propietario','admin','lider','secretario','tesorero','digitador']},
      {label:'Contraseña',field:'Password',type:'password',placeholder:'Dejar vacío para no cambiar'},
    ]}
  />;
}

// ====== BITACORA ======
export function BitacoraPage() {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  useEffect(() => { dispatch('getBitacora').then(d => { setData(Array.isArray(d) ? d : []); setLoading(false); }); }, []);
  return (
    <div>
      <div className="card-hdr"><h2><i className="fas fa-clipboard-list" /> Bitácora de Accesos</h2></div>
      <div className="card" style={{ padding: 0 }}>
        <table className="tb">
          <thead><tr><th>Fecha</th><th>Usuario</th><th>Email</th><th>Rol</th><th>Acción</th><th>Detalle</th></tr></thead>
          <tbody>
            {loading ? <tr><td colSpan={6}><div className="empty"><i className="fas fa-circle-notch fa-spin" /><p>Cargando...</p></div></td></tr> :
             !data.length ? <tr><td colSpan={6}><div className="empty"><i className="fas fa-clipboard-list" /><p>Sin registros</p></div></td></tr> :
             data.slice(0, 200).map((r,i) => (
              <tr key={i}>
                <td style={{fontSize:11}}>{r['FechaHora']}</td>
                <td><b>{r['Usuario']}</b></td>
                <td>{r['Email']}</td>
                <td><span className="bdg bb">{r['Rol']}</span></td>
                <td>{r['Accion']}</td>
                <td style={{fontSize:11,color:'var(--tx2)',maxWidth:200,overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap'}}>{r['Detalles']}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ====== CONFIGURACION ======
export function ConfiguracionPage() {
  const { user, config, loadConfig } = useAuth();
  const [form, setForm] = useState({});
  const [saving, setSaving] = useState(false);
  useEffect(() => { if (config) setForm({ ...config }); }, [config]);

  async function save() {
    setSaving(true);
    try {
      const res = await dispatch('saveConfig', form);
      if (res?.ok) { toast('Configuración guardada', 'ok'); loadConfig(); }
      else toast(res?.msg || 'Error', 'er');
    } catch { toast('Error de conexión', 'er'); }
    setSaving(false);
  }

  const fields = [
    { key: 'nombre', label: 'Nombre del Sistema' },
    { key: 'logoUrl', label: 'URL del Logo' },
    { key: 'ownerEmail', label: 'Email del Propietario' },
    { key: 'formUrlPublic', label: 'URL Formulario Digital' },
    { key: 'metaGrupos', label: 'Meta de Grupos' },
    { key: 'whatsapp_soporte', label: 'WhatsApp Soporte' },
  ];

  return (
    <div>
      <div className="card-hdr"><h2><i className="fas fa-cog" /> Configuración del Sistema</h2></div>
      <div className="card">
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
          {fields.map(f => (
            <div className="fgg" key={f.key}>
              <label>{f.label}</label>
              <input className="fc" value={form[f.key] || ''} onChange={e => setForm({...form, [f.key]: e.target.value})} />
            </div>
          ))}
        </div>
        <div style={{ marginTop: 16 }}>
          <button className="btn btn-ok" onClick={save} disabled={saving}>
            {saving ? <><span className="spinner" /> Guardando...</> : 'Guardar Configuración'}
          </button>
        </div>
      </div>
    </div>
  );
}

// ====== GENERADOR REPORTES ======
export function GeneradorPage() {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filtros, setFiltros] = useState({ desde: '', hasta: '', lider: '', tipo: 'Reporte de Grupos' });

  useEffect(() => { load(); }, []);
  async function load() {
    setLoading(true);
    const res = await dispatch('getGeneradores');
    setData(Array.isArray(res) ? res : []);
    setLoading(false);
  }
  async function generar() {
    setLoading(true);
    const res = await dispatch('generarReporte', { ...filtros, distrito: filtros.distrito || '' });
    if (res?.ok) {
      toast(`Reporte ${res.noSerie} generado`, 'ok');
      if (res.pdfUrl) window.open(res.pdfUrl, '_blank');
    } else toast(res?.msg || 'Error', 'er');
    setLoading(false);
  }

  return (
    <div>
      <div className="card-hdr"><h2><i className="fas fa-file-invoice" /> Generador de Reportes</h2></div>
      <div className="card">
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: 10, marginBottom: 16 }}>
          <div className="fgg"><label>Tipo</label><input className="fc" value={filtros.tipo} onChange={e => setFiltros({...filtros,tipo:e.target.value})} /></div>
          <div className="fgg"><label>Desde</label><input className="fc" type="date" value={filtros.desde} onChange={e => setFiltros({...filtros,desde:e.target.value})} /></div>
          <div className="fgg"><label>Hasta</label><input className="fc" type="date" value={filtros.hasta} onChange={e => setFiltros({...filtros,hasta:e.target.value})} /></div>
          <div className="fgg"><label>Líder</label><input className="fc" value={filtros.lider} onChange={e => setFiltros({...filtros,lider:e.target.value})} /></div>
          <div className="fgg"><label>Distrito</label><input className="fc" value={filtros.distrito||''} onChange={e=>setFiltros({...filtros,distrito:e.target.value})} /></div>
        </div>
        <button className="btn btn-pr" onClick={generar} disabled={loading}>{loading?'Generando...':'Generar Reporte PDF'}</button>
      </div>
      <div className="card" style={{ padding: 0, marginTop: 16 }}>
        <table className="tb">
          <thead><tr><th>No Serie</th><th>Título</th><th>Ofrenda</th><th>Asistencia</th><th>PDF</th></tr></thead>
          <tbody>
            {!data.length ? <tr><td colSpan={5}><div className="empty"><p>Sin reportes generados</p></div></td></tr> :
             data.slice(-20).reverse().map((g,i) => (
              <tr key={i}>
                <td style={{fontFamily:'monospace'}}>{g['No Serie']}</td>
                <td><b>{g['Titulo de Reporte']}</b></td>
                <td>Q{parseFloat(g['Total Ofrenda']||0).toFixed(2)}</td>
                <td>{g['Total Asistencia']}</td>
                <td>{g['Archivo Generado'] && <a href={g['Archivo Generado']} target="_blank" className="btn btn-er btn-sm"><i className="fas fa-file-pdf" /> PDF</a>}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// Placeholders para módulos complejos
export function EnviosPage() {
  return <div className="card"><div className="card-hdr"><h2><i className="fas fa-paper-plane" /> Centro de Envíos</h2></div><div className="empty"><i className="fas fa-paper-plane" /><p>Módulo en construcción. Disponible en la versión completa.</p></div></div>;
}
export function NotificacionesPlaceholder() {
  return <div className="card"><div className="card-hdr"><h2><i className="fas fa-bell" /> Notificaciones</h2></div><div className="empty"><i className="fas fa-bell" /><p>Módulo en construcción. Disponible en la versión completa.</p></div></div>;
}
export function CuadrePage() {
  return <div className="card"><div className="card-hdr"><h2><i className="fas fa-calculator" /> Cuadre Dominical</h2></div><div className="empty"><i className="fas fa-calculator" /><p>Módulo en construcción. Disponible en la versión completa.</p></div></div>;
}