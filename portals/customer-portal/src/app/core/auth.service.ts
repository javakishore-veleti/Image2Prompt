import { Injectable, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, tap } from 'rxjs';
import { environment } from '../../environments/environment';

export interface TokenResponse {
  access_token: string;
  refresh_token?: string;
  token_type: string;
  customer_id: string;
  email: string;
}

const TOKEN_KEY = 'i2p_customer_token';
const REFRESH_KEY = 'i2p_customer_refresh';
const EMAIL_KEY = 'i2p_customer_email';

@Injectable({ providedIn: 'root' })
export class AuthService {
  private base = `${environment.gatewayUrl}/api/customer/auth`;
  readonly email = signal<string | null>(localStorage.getItem(EMAIL_KEY));

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

  signup(email: string, password: string, name: string): Observable<TokenResponse> {
    return this.http
      .post<TokenResponse>(`${this.base}/signup`, { email, password, name })
      .pipe(tap((res) => this.persist(res)));
  }

  login(email: string, password: string): Observable<TokenResponse> {
    return this.http
      .post<TokenResponse>(`${this.base}/login`, { email, password })
      .pipe(tap((res) => this.persist(res)));
  }

  refresh(): Observable<TokenResponse> {
    return this.http
      .post<TokenResponse>(`${this.base}/refresh`, { refresh_token: this.refreshTokenValue })
      .pipe(tap((res) => this.persist(res)));
  }

  logout(): void {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(REFRESH_KEY);
    localStorage.removeItem(EMAIL_KEY);
    this.email.set(null);
  }

  private persist(res: TokenResponse): void {
    localStorage.setItem(TOKEN_KEY, res.access_token);
    if (res.refresh_token) {
      localStorage.setItem(REFRESH_KEY, res.refresh_token);
    }
    localStorage.setItem(EMAIL_KEY, res.email);
    this.email.set(res.email);
  }
}
