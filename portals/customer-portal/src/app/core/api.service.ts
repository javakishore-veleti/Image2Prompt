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

export interface Connection {
  id: string;
  provider: string;
  display_name: string;
  account_email: string | null;
  status: string;
}

export interface DriveFile {
  id: string;
  name: string;
  mime_type: string;
  size: number;
}

export interface ActivityItem {
  id: string;
  created_at: string;
  action: string;
  target: string | null;
  detail: Record<string, unknown>;
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

  // --- Payments / billing (Stripe) ---
  paymentSettings(): Observable<any> {
    return this.http.get(`${this.customer}/me/payment-settings`);
  }
  createSetupIntent(): Observable<{ configured: boolean; client_secret: string | null }> {
    return this.http.post<{ configured: boolean; client_secret: string | null }>(
      `${this.customer}/me/payment-settings/setup-intent`,
      {},
    );
  }
  billing(): Observable<any> {
    return this.http.get(`${this.customer}/me/billing`);
  }

  // --- Projects ---
  projects(): Observable<any[]> {
    return this.http.get<any[]>(`${this.customer}/projects`);
  }
  createProject(name: string): Observable<any> {
    return this.http.post(`${this.customer}/projects`, { name });
  }

  // --- Connections (cloud drives; mock OAuth) ---
  connections(): Observable<Connection[]> {
    return this.http.get<Connection[]>(`${this.customer}/me/connections`);
  }
  connect(provider: string): Observable<Connection> {
    return this.http.post<Connection>(`${this.customer}/me/connections`, { provider });
  }
  googleAuthorize(): Observable<{ authorize_url: string }> {
    return this.http.post<{ authorize_url: string }>(
      `${this.customer}/me/connections/google/authorize`,
      {},
    );
  }
  onedriveAuthorize(): Observable<{ authorize_url: string }> {
    return this.http.post<{ authorize_url: string }>(
      `${this.customer}/me/connections/onedrive/authorize`,
      {},
    );
  }
  disconnect(id: string): Observable<void> {
    return this.http.delete<void>(`${this.customer}/me/connections/${id}`);
  }
  connectionFiles(id: string, search?: string): Observable<DriveFile[]> {
    let params = new HttpParams();
    if (search) {
      params = params.set('search', search);
    }
    return this.http.get<DriveFile[]>(`${this.customer}/me/connections/${id}/files`, { params });
  }

  // --- Providers available to run a request against ---
  availableProviders(): Observable<{ key: string; name: string }[]> {
    return this.http.get<{ key: string; name: string }[]>(`${this.images}/providers`);
  }

  // --- Image processing ---
  generate(file: File, instruction: string, providers?: string, projectId?: string): Observable<ProcRequest> {
    const form = new FormData();
    form.append('image', file);
    form.append('instruction', instruction);
    if (providers) {
      form.append('providers', providers);
    }
    if (projectId) {
      form.append('project_id', projectId);
    }
    return this.http.post<ProcRequest>(`${this.images}/requests`, form);
  }

  requests(): Observable<ProcRequest[]> {
    return this.http.get<ProcRequest[]>(`${this.images}/requests`);
  }

  generateFromConnection(connectionId: string, fileId: string): Observable<ProcRequest> {
    return this.http.post<ProcRequest>(`${this.images}/requests/from-connection`, {
      connection_id: connectionId,
      file_id: fileId,
    });
  }

  activity(limit = 50, offset = 0): Observable<ActivityItem[]> {
    const params = new HttpParams().set('limit', String(limit)).set('offset', String(offset));
    return this.http.get<ActivityItem[]>(`${this.customer}/me/activity`, { params });
  }

  prompts(search?: string): Observable<PromptItem[]> {
    let params = new HttpParams();
    if (search) {
      params = params.set('search', search);
    }
    return this.http.get<PromptItem[]>(`${this.images}/prompts`, { params });
  }
}
