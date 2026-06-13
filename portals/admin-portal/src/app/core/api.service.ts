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
}
