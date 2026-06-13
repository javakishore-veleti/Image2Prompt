import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

export interface ProviderResult {
  id: string;
  provider_key: string;
  status: string;
  output_text: string | null;
  latency_ms: number | null;
  error: any;
  created_at: string;
}

export interface ProcRequest {
  id: string;
  status: string;
  instruction: string;
  file_ref_id: string;
  requested_providers: string[];
  created_at: string;
  providers: ProviderResult[];
}

export interface PromptItem {
  request_id: string;
  provider_result_id: string;
  provider_key: string;
  output_text: string;
  file_ref_id: string;
  created_at: string;
}

export interface Preferences {
  customer_id: string;
  default_provider_keys: string[];
  storage_backend: string;
  prefs: Record<string, unknown>;
}

@Injectable({ providedIn: 'root' })
export class ApiService {
  private customer = `${environment.gatewayUrl}/api/customer`;
  private images = `${environment.gatewayUrl}/api/images`;

  constructor(private http: HttpClient) {}

  // --- Profile / preferences ---
  me(): Observable<any> {
    return this.http.get(`${this.customer}/me`);
  }
  preferences(): Observable<Preferences> {
    return this.http.get<Preferences>(`${this.customer}/me/preferences`);
  }
  updatePreferences(body: Partial<Preferences>): Observable<Preferences> {
    return this.http.put<Preferences>(`${this.customer}/me/preferences`, body);
  }

  // --- Payments / billing (stub) ---
  paymentSettings(): Observable<any> {
    return this.http.get(`${this.customer}/me/payment-settings`);
  }
  billing(): Observable<any> {
    return this.http.get(`${this.customer}/me/billing`);
  }

  // --- Projects ---
  projects(): Observable<any[]> {
    return this.http.get<any[]>(`${this.customer}/projects`);
  }

  // --- Image processing ---
  generate(file: File, instruction: string, providers?: string): Observable<ProcRequest> {
    const form = new FormData();
    form.append('image', file);
    form.append('instruction', instruction);
    if (providers) {
      form.append('providers', providers);
    }
    return this.http.post<ProcRequest>(`${this.images}/requests`, form);
  }

  requests(): Observable<ProcRequest[]> {
    return this.http.get<ProcRequest[]>(`${this.images}/requests`);
  }

  prompts(search?: string): Observable<PromptItem[]> {
    let params = new HttpParams();
    if (search) {
      params = params.set('search', search);
    }
    return this.http.get<PromptItem[]>(`${this.images}/prompts`, { params });
  }
}
