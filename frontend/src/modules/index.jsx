import { useState, useEffect, useCallback } from 'react';
import { dispatch, toast } from '../utils/api';

// Módulo genérico CRUD - maneja listar, crear, editar, eliminar cualquier entidad
export default function CrudModule({ 
  title, icon, 
  getAction, saveAction, deleteAction,
  fields, columns, 
  idField = 'ID',
  extraPayload = {}
}) {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [modalOpen, setModalOpen] = useState(false);
  const [editItem, setEditItem] = useState(null);
  const [formData, setFormData] = useState({});

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await dispatch(getAction, extraPayload);
      const arr = Array.isArray(res) ? res : (res?.data || res?.gastos || []);
      setData(arr);
    } catch (e) {
      toast('Error cargando datos', 'er');
    }
    setLoading(false);
  }, [getAction]);

  useEffect(() => { load(); }, [load]);

  function openNew() {
    setFormData({});
    setEditItem(null);
    setModalOpen(true);
  }

  function openEdit(item) {
    setFormData({ ...item });
    setEditItem(item);
    setModalOpen(true);
  }

  async function save() {
    const payload = { ...formData, ...extraPayload };
    if (editItem?.[idField]) payload[idField] = editItem[idField];
    try {
      const res = await dispatch(saveAction, payload);
      if (res?.ok) {
        toast('Guardado correctamente', 'ok');
        setModalOpen(false);
        load();
      } else {
        toast(res?.msg || 'Error al guardar', 'er');
      }
    } catch (e) {
      toast('Error de conexión', 'er');
    }
  }

  async function remove(item) {
    if (!confirm(`¿Eliminar este registro?`)) return;
    try {
      const res = await dispatch(deleteAction, { [idField]: item[idField], id: item[idField] });
      if (res?.ok) {
        toast('Eliminado', 'ok');
        load();
      } else {
        toast(res?.msg || 'Error al eliminar', 'er');
      }
    } catch (e) {
      toast('Error de conexión', 'er');
    }
  }

  function updateField(field, value) {
    setFormData(prev => ({ ...prev, [field]: value }));
  }

  const filtered = data.filter(item => 
    !search || JSON.stringify(item).toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div>
      <div className="card-hdr" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <h2><i className={icon} /> {title}</h2>
        <div style={{ display: 'flex', gap: 8 }}>
          <input className="fdt" placeholder="Buscar..." value={search} onChange={e => setSearch(e.target.value)} />
          <button className="btn btn-ok btn-sm" onClick={openNew}><i className="fas fa-plus" /> Nuevo</button>
          <button className="btn btn-in btn-sm" onClick={load}><i className="fas fa-sync-alt" /></button>
        </div>
      </div>

      <div className="card" style={{ padding: 0 }}>
        <table className="tb">
          <thead>
            <tr>
              {columns.map((col, i) => <th key={i}>{col.label}</th>)}
              <th style={{ width: 80 }}>Acciones</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={columns.length + 1}><div className="empty"><i className="fas fa-circle-notch fa-spin" /><p>Cargando...</p></div></td></tr>
            ) : !filtered.length ? (
              <tr><td colSpan={columns.length + 1}><div className="empty"><i className="fas fa-inbox" /><p>Sin registros</p></div></td></tr>
            ) : (
              filtered.map((item, i) => (
                <tr key={i}>
                  {columns.map((col, j) => (
                    <td key={j} style={col.style}>
                      {col.render ? col.render(item) : item[col.field]}
                    </td>
                  ))}
                  <td>
                    <div style={{ display: 'flex', gap: 4 }}>
                      <button className="btn btn-in btn-sm" style={{ padding: '4px 8px' }} onClick={() => openEdit(item)}><i className="fas fa-edit" /></button>
                      <button className="btn btn-er btn-sm" style={{ padding: '4px 8px' }} onClick={() => remove(item)}><i className="fas fa-trash-alt" /></button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {modalOpen && (
        <div className="modal-overlay" onClick={() => setModalOpen(false)}>
          <div className="modal-box" onClick={e => e.stopPropagation()}>
            <div className="modal-hdr">
              <span>{editItem ? 'Editar' : 'Nuevo'} {title}</span>
              <button className="btn btn-ol btn-sm" onClick={() => setModalOpen(false)}><i className="fas fa-times" /></button>
            </div>
            <div className="modal-body">
              {fields.map((field, i) => (
                <div className="fgg" key={i}>
                  <label>{field.label} {field.required && <span className="req">*</span>}</label>
                  {field.type === 'textarea' ? (
                    <textarea className="fc" rows={field.rows || 3} value={formData[field.field] || ''}
                              onChange={e => updateField(field.field, e.target.value)} placeholder={field.placeholder} />
                  ) : field.type === 'select' ? (
                    <select className="fc" value={formData[field.field] || ''} 
                            onChange={e => updateField(field.field, e.target.value)}>
                      <option value="">--</option>
                      {field.options.map((opt, j) => <option key={j} value={opt.value || opt}>{opt.label || opt}</option>)}
                    </select>
                  ) : field.type === 'checkbox' ? (
                    <input type="checkbox" checked={formData[field.field] || false}
                           onChange={e => updateField(field.field, e.target.checked)} />
                  ) : (
                    <input className="fc" type={field.type || 'text'} value={formData[field.field] || ''}
                           onChange={e => updateField(field.field, e.target.value)} placeholder={field.placeholder} />
                  )}
                </div>
              ))}
            </div>
            <div className="modal-ft">
              <button className="btn btn-ol" onClick={() => setModalOpen(false)}>Cancelar</button>
              <button className="btn btn-ok" onClick={save}>Guardar</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ====== REPORTES ======
export function ReportesPage() {
  return <CrudModule
    title="Reporte de Grupos" icon="fas fa-file-alt"
    getAction="getReportes"
    saveAction="saveReporte"
    deleteAction="deleteReporte"
    columns={[
      { label: 'Código', field: 'Codigo', style: { fontFamily: 'monospace', fontSize: 12 } },
      { label: 'Líder', field: 'Lider', render: r => <b>{r['Lider']}</b> },
      { label: 'Fecha', field: 'Fecha' },
      { label: 'Grupo', field: 'Grupo' },
      { label: 'Asistencia', field: 'Asistencia Grupo Familiar', style: { fontWeight: 700, textAlign: 'center' } },
      { label: 'Ofrenda', field: 'Ofrenda Total', render: r => `Q${parseFloat(r['Ofrenda Total'] || 0).toFixed(2)}`, style: { fontWeight: 700, textAlign: 'right' } },
      { label: 'Estado', field: 'Ofrenda Recibida', render: r => <span className={`bdg ${r['Ofrenda Recibida'] === 'Pendiente' ? 'bo' : 'bg'}`}>{r['Ofrenda Recibida'] || 'Pendiente'}</span> },
    ]}
    fields={[
      { label: 'Código Líder', field: 'CodigoL', required: true },
      { label: 'Líder', field: 'NombreL', required: true },
      { label: 'Fecha', field: 'Fecha', type: 'date' },
      { label: 'Distrito', field: 'Distrito' },
      { label: 'Zona', field: 'Zona' },
      { label: 'Asistencia', field: 'Asistencia Grupo Familiar', type: 'number' },
      { label: 'Ofrenda Total', field: 'Ofrenda Total', type: 'number' },
      { label: 'Ofrenda Recibida', field: 'Ofrenda Recibida', type: 'select', options: ['Recibida', 'Pendiente'] },
      { label: 'Tipo de Reporte', field: 'Tipo de Reporte', type: 'select', options: ['Mixta (Reunión Regular)', 'Jóvenes', 'Damas', 'Caballeros', 'Niños'] },
    ]}
  />;
}

// ====== HERMANOS ======
export function HermanosPage() {
  return <CrudModule
    title="Hermanos Líderes" icon="fas fa-user-tie"
    getAction="getHermanos"
    saveAction="saveHermano"
    deleteAction="deleteHermano"
    columns={[
      { label: 'Código', field: 'CodigoL', style: { fontFamily: 'monospace' } },
      { label: 'Nombre', field: 'NombreL', render: h => <b>{h['NombreL']}</b> },
      { label: 'Distrito', field: 'Distrito' },
      { label: 'Zona', field: 'Zona' },
      { label: 'Área', field: 'Area' },
      { label: 'Sector', field: 'Sector' },
      { label: 'Grupo', field: 'Grupo' },
      { label: 'Pastor Zona', field: 'Pastor Zona' },
    ]}
    fields={[
      { label: 'Código Líder', field: 'CodigoL', required: true },
      { label: 'Nombre', field: 'NombreL', required: true },
      { label: 'Distrito', field: 'Distrito' },
      { label: 'Zona', field: 'Zona' },
      { label: 'Área', field: 'Area' },
      { label: 'Sector', field: 'Sector' },
      { label: 'Grupo', field: 'Grupo' },
      { label: 'Pastor Zona', field: 'Pastor Zona' },
      { label: 'Sup Sector', field: 'Sup SectorL' },
      { label: 'Sup Área', field: 'Sup AreaL' },
      { label: 'Ayuda Pastor', field: 'Ayuda Pastor' },
      { label: 'Anfitrión', field: 'Anfitrion' },
      { label: 'Dirección', field: 'Direccion', type: 'textarea', rows: 2 },
    ]}
  />;
}

// ====== DIEZMOS ======
export function DiezmosPage() {
  return <CrudModule
    title="Control de Diezmos" icon="fas fa-coins"
    getAction="getDiezmos"
    saveAction="saveDiezmo"
    deleteAction="deleteDiezmo"
    columns={[
      { label: 'Fecha', field: 'Fecha' },
      { label: 'Nombre', field: 'Nombre', render: d => <b>{d['Nombre']}</b> },
      { label: 'Tipo', field: 'Tipo', render: d => <span className="bdg bb">{d['Tipo']}</span> },
      { label: 'Monto', field: 'MontoQ', render: d => <span style={{ fontWeight: 800, color: 'var(--ok)' }}>Q{parseFloat(d['MontoQ'] || 0).toFixed(2)}</span>, style: { textAlign: 'right' } },
    ]}
    fields={[
      { label: 'Fecha', field: 'Fecha', type: 'date' },
      { label: 'Nombre', field: 'Nombre', required: true },
      { label: 'Monto', field: 'MontoQ', type: 'number' },
      { label: 'Tipo', field: 'Tipo', type: 'select', options: ['Diezmo', 'Ofrenda', 'Siembra', 'Pacto', 'Primicia'] },
      { label: 'Descripción', field: 'Descripcion', type: 'textarea', rows: 2 },
    ]}
  />;
}

// ====== GASTOS ======
export function GastosPage() {
  return <CrudModule
    title="Control de Gastos" icon="fas fa-receipt"
    getAction="getGastos"
    saveAction="saveGasto"
    deleteAction="deleteGasto"
    columns={[
      { label: 'Fecha', field: 'Fecha' },
      { label: 'Concepto', field: 'Concepto', render: g => <b>{g['Concepto']}</b> },
      { label: 'Categoría', field: 'Categoria', render: g => <span className="bdg bb">{g['Categoria']}</span> },
      { label: 'Monto', field: 'MontoQ', render: g => <span style={{ fontWeight: 800, color: 'var(--er)' }}>Q{parseFloat(g['MontoQ'] || 0).toFixed(2)}</span>, style: { textAlign: 'right' } },
      { label: 'Responsable', field: 'Responsable' },
    ]}
    fields={[
      { label: 'Fecha', field: 'Fecha', type: 'date' },
      { label: 'Concepto', field: 'Concepto', required: true },
      { label: 'Monto', field: 'MontoQ', type: 'number' },
      { label: 'Categoría', field: 'Categoria', type: 'select', options: ['Limpieza', 'Mantenimiento', 'Eventos', 'Papelería', 'Transporte', 'Alimentación', 'Servicios', 'Otro'] },
      { label: 'Responsable', field: 'Responsable' },
      { label: 'Método', field: 'Metodo', type: 'select', options: ['Efectivo', 'Transferencia', 'Tarjeta'] },
      { label: 'Descripción', field: 'Descripcion', type: 'textarea', rows: 2 },
    ]}
  />;
}

// ====== CONTACTOS ======
export function ContactosPage() {
  return <CrudModule
    title="Tabla de Contactos" icon="fas fa-address-book"
    getAction="getContactos"
    saveAction="saveContacto"
    deleteAction="deleteContacto"
    idField="IDContacto"
    columns={[
      { label: 'Nombre', field: 'Nombre', render: c => <b>{c['Nombre']}</b> },
      { label: 'Correo', field: 'Correo' },
      { label: 'WhatsApp', field: 'WhatsApp' },
    ]}
    fields={[
      { label: 'Nombre', field: 'Nombre', required: true },
      { label: 'Correo', field: 'Correo', type: 'email' },
      { label: 'WhatsApp', field: 'WhatsApp', placeholder: '+502 XXXX-XXXX' },
      { label: 'Dirección', field: 'Direccion' },
    ]}
  />;
}

// Placeholder pages for modules not yet fully built
export function SupervisoresPage() {
  return <CrudModule title="Supervisores" icon="fas fa-user-shield" getAction="getSupervisores" saveAction="saveSupervisor" deleteAction="deleteSupervisor"
    columns={[{label:'Código',field:'CodigoSup'},{label:'Nombre',field:'NombreSup'},{label:'Distrito',field:'Distrito'},{label:'Zona',field:'Zona'}]}
    fields={[{label:'Código',field:'CodigoSup',required:true},{label:'Nombre',field:'NombreSup',required:true},{label:'Distrito',field:'Distrito'},{label:'Zona',field:'Zona'},{label:'Área',field:'Area'},{label:'Teléfono',field:'Telefono'},{label:'Email',field:'Email'}]}
  />;
}

export function PastoresPage() {
  return <CrudModule title="Pastores" icon="fas fa-church" getAction="getPastores" saveAction="savePastor" deleteAction="deletePastor"
    columns={[{label:'Código',field:'CodigoPastor'},{label:'Nombre',field:'NombrePastor'},{label:'Distrito',field:'Distrito'}]}
    fields={[{label:'Código',field:'CodigoPastor',required:true},{label:'Nombre',field:'NombrePastor',required:true},{label:'Distrito',field:'Distrito'},{label:'Zona',field:'Zona'},{label:'Teléfono',field:'Telefono'},{label:'Email',field:'Email'}]}
  />;
}

export function SeguimientosPage() {
  return <CrudModule title="Seguimientos" icon="fas fa-user-check" getAction="getSeguimientos" saveAction="saveSeguimiento" deleteAction="deleteSeguimiento"
    columns={[{label:'Fecha',field:'Fecha'},{label:'Persona',field:'Persona'},{label:'Tipo',field:'Tipo'},{label:'Responsable',field:'Responsable'},{label:'Estado',field:'Estado',render: s => <span className={`bdg ${s['Estado']==='Completado'?'bg':'bo'}`}>{s['Estado']}</span>}]}
    fields={[{label:'Persona',field:'Persona',required:true},{label:'Tipo',field:'Tipo',type:'select',options:['Convertido','Reconciliación','Visita','Sanidad','Oración']},{label:'Responsable',field:'Responsable'},{label:'Estado',field:'Estado',type:'select',options:['Pendiente','En Proceso','Completado']},{label:'Observaciones',field:'Observaciones',type:'textarea',rows:3}]}
  />;
}

export function BautizosPage() {
  return <CrudModule title="Bautizos" icon="fas fa-water" getAction="getBautizos" saveAction="saveBautizo" deleteAction="deleteBautizo"
    columns={[{label:'Fecha',field:'Fecha'},{label:'Nombre',field:'Nombre'},{label:'Edad',field:'Edad'},{label:'Pastor',field:'PastorOficiante'},{label:'Lugar',field:'Lugar'}]}
    fields={[{label:'Fecha',field:'Fecha',type:'date'},{label:'Nombre',field:'Nombre',required:true},{label:'Edad',field:'Edad',type:'number'},{label:'Teléfono',field:'Telefono'},{label:'Pastor',field:'PastorOficiante'},{label:'Lugar',field:'Lugar'},{label:'Observaciones',field:'Observaciones',type:'textarea',rows:2}]}
  />;
}