import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { map } from 'rxjs/operators';
import { environment } from '../../environments/environment';

export interface Page<T> {
  items: T[];
  total: number;
}

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

export interface StackPrice {
  stack: string;
  monthly_cost: number;
}

export interface Plan {
  id: string;
  name: string;
  description: string | null;
  status: string;
  stacks: StackPrice[];
  max_kbs: number | null;
  max_docs_per_kb: number | null;
}

export interface SubscriptionRow {
  id: string;
  customer_id: string;
  customer_email: string | null;
  plan_id: string;
  status: string;
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
  unlockCustomer(customerId: string): Observable<{ message: string }> {
    return this.http.post<{ message: string }>(`${this.admin}/customers/${customerId}/unlock`, {});
  }
  unlockAdmin(id: string): Observable<{ message: string }> {
    return this.http.post<{ message: string }>(`${this.admin}/users/${id}/unlock`, {});
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

  // --- Subscriptions ---
  techStacks(): Observable<string[]> {
    return this.http.get<string[]>(`${this.admin}/subscriptions/tech-stacks`);
  }
  revenue(): Observable<{
    total_mrr: number;
    plans: { plan_id: string; plan_name: string; customers: number; plan_price: number; mrr: number }[];
  }> {
    return this.http.get<any>(`${this.admin}/subscriptions/revenue`);
  }
  plans(search?: string): Observable<Plan[]> {
    let params = new HttpParams();
    if (search) params = params.set('search', search);
    return this.http.get<Plan[]>(`${this.admin}/subscriptions`, { params });
  }
  createPlan(body: Partial<Plan>): Observable<Plan> {
    return this.http.post<Plan>(`${this.admin}/subscriptions`, body);
  }
  updatePlan(id: string, body: Partial<Plan>): Observable<Plan> {
    return this.http.patch<Plan>(`${this.admin}/subscriptions/${id}`, body);
  }
  assignCustomer(planId: string, body: { customer_id: string; customer_email?: string }): Observable<SubscriptionRow> {
    return this.http.post<SubscriptionRow>(`${this.admin}/subscriptions/${planId}/customers`, body);
  }
  planCustomers(planId: string, search?: string): Observable<SubscriptionRow[]> {
    let params = new HttpParams();
    if (search) params = params.set('search', search);
    return this.http.get<SubscriptionRow[]>(`${this.admin}/subscriptions/${planId}/customers`, { params });
  }

  auditLog(filter: AuditFilter = {}, offset = 0): Observable<Page<AuditEntry>> {
    let params = this.auditParams(filter);
    if (offset) {
      params = params.set('offset', String(offset));
    }
    return this.http
      .get<AuditEntry[]>(`${this.admin}/audit-log`, { params, observe: 'response' })
      .pipe(
        map((r) => ({
          items: r.body ?? [],
          total: Number(r.headers.get('X-Total-Count') ?? (r.body?.length ?? 0)),
        })),
      );
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
