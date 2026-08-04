import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import Layout from './components/Layout';
import LoginPage from './pages/Login';
import Dashboard from './pages/Dashboard';
import { 
  ReportesPage, HermanosPage, DiezmosPage, GastosPage, ContactosPage,
  SupervisoresPage, PastoresPage, SeguimientosPage, BautizosPage
} from './modules/index';
import {
  InventarioPage, InsumosPage, UsuariosPage, BitacoraPage,
  ConfiguracionPage, GeneradorPage, EnviosPage, NotificacionesPlaceholder, CuadrePage
} from './modules/MoreModules';

function ProtectedRoute({ children }) {
  const { user, loading } = useAuth();
  if (loading) return <div className="login-bg"><div className="spinner" /></div>;
  if (!user) return <Navigate to="/login" />;
  return children;
}

function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/" element={<ProtectedRoute><Layout /></ProtectedRoute>}>
        <Route index element={<Dashboard />} />
        <Route path="dashboard" element={<Dashboard />} />
        <Route path="reportes" element={<ReportesPage />} />
        <Route path="hermanos" element={<HermanosPage />} />
        <Route path="diezmos" element={<DiezmosPage />} />
        <Route path="gastos" element={<GastosPage />} />
        <Route path="contactos" element={<ContactosPage />} />
        <Route path="supervisores" element={<SupervisoresPage />} />
        <Route path="pastores" element={<PastoresPage />} />
        <Route path="ayudapastor" element={<PastoresPage />} />
        <Route path="seguimientos" element={<SeguimientosPage />} />
        <Route path="bautizos" element={<BautizosPage />} />
        <Route path="inventario" element={<InventarioPage />} />
        <Route path="insumos" element={<InsumosPage />} />
        <Route path="usuarios" element={<UsuariosPage />} />
        <Route path="bitacora" element={<BitacoraPage />} />
        <Route path="configuracion" element={<ConfiguracionPage />} />
        <Route path="generador" element={<GeneradorPage />} />
        <Route path="envio" element={<EnviosPage />} />
        <Route path="notificaciones" element={<NotificacionesPlaceholder />} />
        <Route path="cuadre" element={<CuadrePage />} />
        <Route path="*" element={<Dashboard />} />
      </Route>
    </Routes>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </BrowserRouter>
  );
}