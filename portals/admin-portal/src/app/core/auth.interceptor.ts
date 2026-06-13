import { HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { catchError, switchMap, throwError } from 'rxjs';
import { AuthService } from './auth.service';

const TOKEN_KEY = 'i2p_admin_token';

/** Attaches the admin bearer token; on a 401, refreshes once and retries, else
 * redirects to sign-in. */
export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const auth = inject(AuthService);
  const router = inject(Router);

  const token = localStorage.getItem(TOKEN_KEY);
  const authed = token ? req.clone({ setHeaders: { Authorization: `Bearer ${token}` } }) : req;

  return next(authed).pipe(
    catchError((err) => {
      const isAuthCall = req.url.includes('/auth/');
      if (err?.status === 401 && !isAuthCall && auth.refreshTokenValue) {
        return auth.refresh().pipe(
          switchMap((res) =>
            next(req.clone({ setHeaders: { Authorization: `Bearer ${res.access_token}` } })),
          ),
          catchError((refreshErr) => {
            auth.logout();
            router.navigateByUrl('/signin');
            return throwError(() => refreshErr);
          }),
        );
      }
      return throwError(() => err);
    }),
  );
};
