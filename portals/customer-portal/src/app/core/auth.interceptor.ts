import { HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { catchError, switchMap, throwError } from 'rxjs';
import { AuthService } from './auth.service';

const TOKEN_KEY = 'i2p_customer_token';

/** Attaches the bearer token, and on a 401 transparently refreshes once and
 * retries the original request (then redirects to sign-in if refresh fails). */
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
