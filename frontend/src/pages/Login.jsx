import { useState } from 'react';
import { login, firebaseLogin } from '../utils/api';
import { toast } from '../utils/api';

export default function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!email || !password) return toast('Completa todos los campos', 'wa');
    setLoading(true);
    try {
      const res = await login(email, password);
      if (res.ok) {
        window.location.href = '/';
      } else {
        toast(res.msg || 'Credenciales inválidas', 'er');
      }
    } catch (err) {
      toast('Error de conexión', 'er');
    }
    setLoading(false);
  };

  return (
    <div className="login-bg">
      <div className="login-card" style={{ animation: 'fadeIn .4s ease' }}>
        <img src="/logo.png" alt="Logo" className="login-logo" 
             onError={(e) => { e.target.style.display = 'none'; }} />
        <h2 style={{ fontSize: 22, fontWeight: 900, color: 'var(--pr)', marginBottom: 6 }}>REDIL</h2>
        <p style={{ fontSize: 13, color: 'var(--tx2)', marginBottom: 24 }}>Sistema de Gestión Eclesiástica</p>
        <form onSubmit={handleSubmit}>
          <div style={{ marginBottom: 14 }}>
            <input type="email" className="login-input" placeholder="Correo electrónico" 
                   value={email} onChange={e => setEmail(e.target.value)} />
          </div>
          <div style={{ marginBottom: 20 }}>
            <input type="password" className="login-input" placeholder="Contraseña"
                   value={password} onChange={e => setPassword(e.target.value)} />
          </div>
          <button type="submit" className="btn btn-pr btn-lg" style={{ width: '100%', justifyContent: 'center' }}
                  disabled={loading}>
            {loading ? <><span className="spinner" /> Ingresando...</> : 'Iniciar Sesión'}
          </button>
        </form>
        <div style={{ marginTop: 16, fontSize: 12, color: 'var(--tx3)' }}>
          Iglesia Restauración · v2.0
        </div>
      </div>
    </div>
  );
}