import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:5000',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Interceptor to inject token on requests
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('linkly_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Interceptor to handle session expiration
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response) {
      const status = error.response.status;
      const url = error.config.url || '';
      
      // If we receive a 401 (Unauthorized) or 403 (Forbidden) and we are not querying login/registration,
      // it means the token is expired or invalid. Perform auto logout.
      if ((status === 401 || status === 403) && !url.includes('/login') && !url.includes('/register') && !url.includes('/verify-email')) {
        localStorage.removeItem('linkly_token');
        localStorage.removeItem('linkly_user');
        // Dispatch custom event or redirect
        window.dispatchEvent(new Event('auth_session_expired'));
      }
    }
    return Promise.reject(error);
  }
);

export default api;
