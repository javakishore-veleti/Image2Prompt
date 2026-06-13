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

  updateProvider(id: string, body: Partial<Provider>): Observable<Provider> {
    return this.http.patch<Provider>(`${this.admin}/providers/${id}`, body);
  }
}
