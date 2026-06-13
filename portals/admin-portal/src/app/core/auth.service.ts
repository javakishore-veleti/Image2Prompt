import { Injectable, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, tap } from 'rxjs';
import { environment } from '../../environments/environment';

export interface AdminTokenResponse {
  access_token: string;
  token_type: string;
  email: string;
  role: string;
}

const TOKEN_KEY = 'i2p_admin_token';
const EMAIL_KEY = 'i2p_admin_email';

@Injectable({ providedIn: 'root' })
export class AuthService {
  private base = `${environment.gatewayUrl}/api/admin/auth`;
  readonly email = signal<string | null>(localStorage.getItem(EMAIL_KEY));

  constructor(private http: HttpClient) {}

  get token(): string | null {
    return localStorage.getItem(TOKEN_KEY);
  }
  get isAuthenticated(): boolean {
    return !!this.token;
  }

  login(email: string, password: string): Observable<AdminTokenResponse> {
    return this.http
      .post<AdminTokenResponse>(`${this.base}/login`, { email, password })
      .pipe(
        tap((res) => {
          localStorage.setItem(TOKEN_KEY, res.access_token);
          localStorage.setItem(EMAIL_KEY, res.email);
          this.email.set(res.email);
        }),
      );
  }

  logout(): void {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(EMAIL_KEY);
    this.email.set(null);
  }
}
