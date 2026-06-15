import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { map } from 'rxjs/operators';
import { environment } from '../../environments/environment';

export interface Page<T> {
  items: T[];
  total: number;
}

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

export interface KbGroup {
  id: string;
  project_id: string;
  name: string;
  created_at: string;
}

export interface ProjectKb {
  id: string;
  group_id: string;
  project_id: string;
  name: string;
  tech_stack: string;
  status: string;
  doc_count: number;
  backend_ready: boolean;
}

export interface KbDoc {
  id: string;
  generation_id: string;
  title: string | null;
  created_at: string;
}

export interface KbResult {
  generation_id: string;
  score: number;
  title: string | null;
  project_id: string | null;
}

@Injectable({ providedIn: 'root' })
export class ApiService {
  private customer = `${environment.gatewayUrl}/api/customer`;
  private images = `${environment.gatewayUrl}/api/images`;
  private kb = `${environment.gatewayUrl}/api/kb`;

  constructor(private http: HttpClient) {}

  // --- Knowledge Bank (Project KB) ---
  kbTechStacks(): Observable<string[]> {
    return this.http.get<string[]>(`${this.kb}/tech-stacks`);
  }
  kbGroups(projectId: string): Observable<KbGroup[]> {
    return this.http.get<KbGroup[]>(`${this.kb}/groups`, { params: new HttpParams().set('project_id', projectId) });
  }
  createKbGroup(projectId: string, name: string): Observable<KbGroup> {
    return this.http.post<KbGroup>(`${this.kb}/groups`, { project_id: projectId, name });
  }
  kbs(groupId: string): Observable<ProjectKb[]> {
    return this.http.get<ProjectKb[]>(`${this.kb}/kbs`, { params: new HttpParams().set('group_id', groupId) });
  }
  createKb(body: { group_id: string; project_id: string; name: string; tech_stack: string }): Observable<ProjectKb> {
    return this.http.post<ProjectKb>(`${this.kb}/kbs`, body);
  }
  kbDocuments(kbId: string): Observable<KbDoc[]> {
    return this.http.get<KbDoc[]>(`${this.kb}/kbs/${kbId}/documents`);
  }
  ingestKb(kbId: string, generationIds: string[]): Observable<{ ingested: number; skipped: number; doc_count: number }> {
    return this.http.post<{ ingested: number; skipped: number; doc_count: number }>(
      `${this.kb}/kbs/${kbId}/ingest`,
      { generation_ids: generationIds },
    );
  }
  queryKb(kbId: string, query: string, topK = 5): Observable<{ results: KbResult[] }> {
    return this.http.post<{ results: KbResult[] }>(`${this.kb}/kbs/${kbId}/query`, { query, top_k: topK });
  }

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
  chargeSubscription(): Observable<any> {
    return this.http.post(`${this.customer}/me/billing/invoice`, {});
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

  activity(limit = 50, offset = 0): Observable<Page<ActivityItem>> {
    const params = new HttpParams().set('limit', String(limit)).set('offset', String(offset));
    return this.http
      .get<ActivityItem[]>(`${this.customer}/me/activity`, { params, observe: 'response' })
      .pipe(
        map((r) => ({
          items: r.body ?? [],
          total: Number(r.headers.get('X-Total-Count') ?? (r.body?.length ?? 0)),
        })),
      );
  }

  prompts(search?: string): Observable<PromptItem[]> {
    let params = new HttpParams();
    if (search) {
      params = params.set('search', search);
    }
    return this.http.get<PromptItem[]>(`${this.images}/prompts`, { params });
  }
}
