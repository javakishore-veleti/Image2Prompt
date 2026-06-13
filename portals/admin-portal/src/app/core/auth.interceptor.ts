import { HttpInterceptorFn } from '@angular/common/http';

const TOKEN_KEY = 'i2p_admin_token';

/** Attaches the admin bearer token to gateway requests. */
export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const token = localStorage.getItem(TOKEN_KEY);
  if (token) {
    req = req.clone({ setHeaders: { Authorization: `Bearer ${token}` } });
  }
  return next(req);
};
