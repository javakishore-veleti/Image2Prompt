import { Injectable, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, tap } from 'rxjs';
import { environment } from '../../environments/environment';

export interface AdminTokenResponse {
  access_token: string;
  refresh_token?: string;
  token_type: string;
  email: string;
  role: string;
}

const TOKEN_KEY = 'i2p_admin_token';
const REFRESH_KEY = 'i2p_admin_refresh';
const EMAIL_KEY = 'i2p_admin_email';
const ROLE_KEY = 'i2p_admin_role';

@Injectable({ providedIn: 'root' })
export class AuthService {
  private base = `${environment.gatewayUrl}/api/admin/auth`;
  readonly email = signal<string | null>(localStorage.getItem(EMAIL_KEY));
  readonly role = signal<string | null>(localStorage.getItem(ROLE_KEY));

  get isSuperadmin(): boolean {
    return this.role() === 'superadmin';
  }

  constructor(private http: HttpClient) {}

  get token(): string | null {
    return localStorage.getItem(TOKEN_KEY);
  }
  get refreshTokenValue(): string | null {
    return localStorage.getItem(REFRESH_KEY);
  }
  get isAuthenticated(): boolean {
    return !!this.token;
  }

  login(email: string, password: string): Observable<AdminTokenResponse> {
    return this.http
      .post<AdminTokenResponse>(`${this.base}/login`, { email, password })
      .pipe(tap((res) => this.persist(res)));
  }

  refresh(): Observable<AdminTokenResponse> {
    return this.http
      .post<AdminTokenResponse>(`${this.base}/refresh`, { refresh_token: this.refreshTokenValue })
      .pipe(tap((res) => this.persist(res)));
  }

  logout(): void {
    const rt = this.refreshTokenValue;
    if (rt) {
      this.http.post(`${this.base}/logout`, { refresh_token: rt }).subscribe({ error: () => {} });
    }
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(REFRESH_KEY);
    localStorage.removeItem(EMAIL_KEY);
    localStorage.removeItem(ROLE_KEY);
    this.email.set(null);
    this.role.set(null);
  }

  private persist(res: AdminTokenResponse): void {
    localStorage.setItem(TOKEN_KEY, res.access_token);
    if (res.refresh_token) {
      localStorage.setItem(REFRESH_KEY, res.refresh_token);
    }
    localStorage.setItem(EMAIL_KEY, res.email);
    localStorage.setItem(ROLE_KEY, res.role);
    this.email.set(res.email);
    this.role.set(res.role);
  }
}
