import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

export interface Customer {
  id: string;
  email: string;
  name: string | null;
  status: string | null;
}

export interface Provider {
  id: string;
  key: string;
  name: string;
  category: string;
  enabled: boolean;
  config: Record<string, unknown>;
}

export interface CspViolation {
  id: string;
  created_at: string;
  document_uri: string | null;
  violated_directive: string | null;
  blocked_uri: string | null;
  source_file: string | null;
  line_number: number | null;
  disposition: string | null;
}

export interface CspDashboard {
  total: number;
  summary: { directive: string; count: number }[];
  violations: CspViolation[];
}

@Injectable({ providedIn: 'root' })
export class ApiService {
  private admin = `${environment.gatewayUrl}/api/admin`;

  constructor(private http: HttpClient) {}

  customers(search?: string): Observable<Customer[]> {
    let params = new HttpParams();
    if (search) {
      params = params.set('search', search);
    }
    return this.http.get<Customer[]>(`${this.admin}/customers`, { params });
  }

  providers(): Observable<Provider[]> {
    return this.http.get<Provider[]>(`${this.admin}/providers`);
  }

  customerConnections(customerId: string): Observable<any[]> {
    return this.http.get<any[]>(`${this.admin}/customers/${customerId}/connections`);
  }

  customerActivity(customerId: string): Observable<AuditEntry[]> {
    return this.http.get<AuditEntry[]>(`${this.admin}/customers/${customerId}/activity`);
  }

  analytics(): Observable<any> {
    return this.http.get(`${this.admin}/analytics`);
  }

  admins(): Observable<any[]> {
    return this.http.get<any[]>(`${this.admin}/users`);
  }
  createAdmin(body: { email: string; password: string; role: string }): Observable<any> {
    return this.http.post(`${this.admin}/users`, body);
  }
  updateAdmin(id: string, body: { role?: string; password?: string }): Observable<any> {
    return this.http.patch(`${this.admin}/users/${id}`, body);
  }
  deleteAdmin(id: string): Observable<void> {
    return this.http.delete<void>(`${this.admin}/users/${id}`);
  }

  updateProvider(id: string, body: Partial<Provider>): Observable<Provider> {
    return this.http.patch<Provider>(`${this.admin}/providers/${id}`, body);
  }

  cspViolations(limit = 100): Observable<CspDashboard> {
    let params = new HttpParams().set('limit', String(limit));
    return this.http.get<CspDashboard>(`${this.admin}/csp-violations`, { params });
  }

  pruneNow(): Observable<{ revoked_tokens: number; csp_violations: number }> {
    return this.http.post<{ revoked_tokens: number; csp_violations: number }>(
      `${this.admin}/maintenance/prune`,
      {},
    );
  }

  reencryptSecrets(): Observable<{ providers: number; connections: number }> {
    return this.http.post<{ providers: number; connections: number }>(
      `${this.admin}/maintenance/reencrypt`,
      {},
    );
  }

  rotationStatus(): Observable<RotationStatus> {
    return this.http.get<RotationStatus>(`${this.admin}/maintenance/rotation-status`);
  }

  auditLog(filter: AuditFilter = {}, offset = 0): Observable<AuditEntry[]> {
    let params = this.auditParams(filter);
    if (offset) {
      params = params.set('offset', String(offset));
    }
    return this.http.get<AuditEntry[]>(`${this.admin}/audit-log`, { params });
  }

  exportAudit(filter: AuditFilter = {}): Observable<Blob> {
    return this.http.get(`${this.admin}/audit-log/export`, {
      params: this.auditParams(filter),
      responseType: 'blob',
    });
  }

  private auditParams(f: AuditFilter): HttpParams {
    let p = new HttpParams();
    if (f.action) p = p.set('action', f.action);
    if (f.actor) p = p.set('actor', f.actor);
    if (f.days) p = p.set('days', String(f.days));
    return p;
  }
}

export interface AuditFilter {
  action?: string;
  actor?: string;
  days?: number;
}

export interface RotationStatus {
  key_id: string | null;
  providers: { total: number; stale: number };
  connections: { total: number; stale: number };
}

export interface AuditEntry {
  id: string;
  created_at: string;
  actor_email: string | null;
  action: string;
  target: string | null;
  detail: Record<string, unknown>;
}
