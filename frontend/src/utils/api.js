const API_BASE = '/api';

export async function dispatch(action, payload = {}) {
  const token = localStorage.getItem('token');
  const res = await fetch(`${API_BASE}/dispatch`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ action, payload: { ...payload, token } }),
  });
  return res.json();
}

export async function login(email, password) {
  const res = await dispatch('login', { email, password });
  if (res.ok) {
    localStorage.setItem('token', res.token);
    localStorage.setItem('user', JSON.stringify(res.user));
  }
  return res;
}

export async function firebaseLogin(idToken) {
  const res = await dispatch('firebaseLogin', { idToken });
  if (res.ok) {
    localStorage.setItem('token', res.token);
    localStorage.setItem('user', JSON.stringify(res.user));
  }
  return res;
}

export function logout() {
  localStorage.removeItem('token');
  localStorage.removeItem('user');
  window.location.href = '/login';
}

export function getUser() {
  try {
    return JSON.parse(localStorage.getItem('user'));
  } catch {
    return null;
  }
}

export function getToken() {
  return localStorage.getItem('token');
}

export function isAuthenticated() {
  return !!getToken();
}

export function toast(msg, type = 'ok') {
  const container = document.getElementById('toast-container');
  if (!container) return;
  const el = document.createElement('div');
  el.className = `toast toast-${type}`;
  const icons = { ok: '✅', er: '❌', wa: '⚠️' };
  el.innerHTML = `${icons[type] || ''} ${msg}`;
  container.appendChild(el);
  setTimeout(() => el.remove(), 4000);
}