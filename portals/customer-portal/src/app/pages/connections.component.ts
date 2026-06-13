import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService, Connection, DriveFile } from '../core/api.service';

@Component({
  selector: 'app-connections',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <h2 class="page-title">Connections</h2>
    <div class="card">
      <p class="muted">Connect a cloud drive to browse images. (OAuth is mocked in this build.)</p>
      <div class="connect-row">
        <button *ngFor="let p of available" class="ghost" (click)="connectProvider(p.key)" [disabled]="busy()">
          + {{ p.label }}{{ p.key === 'google_drive' ? ' (OAuth)' : '' }}
        </button>
      </div>
      <p class="error" *ngIf="error()">{{ error() }}</p>
    </div>

    <div class="card conn" *ngFor="let c of connections()">
      <div class="conn-head">
        <div>
          <strong>{{ c.display_name }}</strong>
          <span class="muted">· {{ c.account_email }}</span>
          <span class="ok">· {{ c.status }}</span>
        </div>
        <button class="ghost" (click)="disconnect(c)">Disconnect</button>
      </div>
      <div class="files">
        <input placeholder="Search files…" [(ngModel)]="searchText[c.id]" (keyup.enter)="loadFiles(c)" />
        <button class="ghost" (click)="loadFiles(c)">Browse</button>
      </div>
      <ul *ngIf="files()[c.id]?.length">
        <li *ngFor="let f of files()[c.id]">{{ f.name }} <span class="muted">({{ f.mime_type }})</span></li>
      </ul>
    </div>

    <p class="muted" *ngIf="connections().length === 0">No connections yet.</p>
  `,
  styles: [
    `
      .connect-row { display: flex; gap: 10px; flex-wrap: wrap; }
      .conn { margin-top: 14px; }
      .conn-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
      .files { display: flex; gap: 10px; max-width: 480px; margin-bottom: 8px; }
      ul { margin: 0; padding-left: 18px; }
      li { margin: 3px 0; }
    `,
  ],
})
export class ConnectionsComponent {
  private api = inject(ApiService);

  available = [
    { key: 'google_drive', label: 'Google Drive' },
    { key: 'onedrive', label: 'OneDrive' },
    { key: 'dropbox', label: 'Dropbox' },
  ];
  connections = signal<Connection[]>([]);
  files = signal<Record<string, DriveFile[]>>({});
  searchText: Record<string, string> = {};
  busy = signal(false);
  error = signal('');

  constructor() {
    this.load();
  }

  load(): void {
    this.api.connections().subscribe({ next: (c) => this.connections.set(c), error: () => {} });
  }

  connectProvider(provider: string): void {
    if (provider === 'google_drive') {
      // Real OAuth: get the consent URL, then send the browser to Google.
      this.error.set('');
      this.busy.set(true);
      this.api.googleAuthorize().subscribe({
        next: (r) => (window.location.href = r.authorize_url),
        error: (err) => {
          this.busy.set(false);
          this.error.set(err?.error?.detail ?? 'Google is not configured');
        },
      });
      return;
    }
    this.connect(provider);
  }

  connect(provider: string): void {
    this.error.set('');
    this.busy.set(true);
    this.api.connect(provider).subscribe({
      next: () => {
        this.busy.set(false);
        this.load();
      },
      error: (err) => {
        this.busy.set(false);
        this.error.set(err?.error?.detail ?? 'Connect failed');
      },
    });
  }

  disconnect(c: Connection): void {
    this.api.disconnect(c.id).subscribe({ next: () => this.load(), error: () => {} });
  }

  loadFiles(c: Connection): void {
    this.api.connectionFiles(c.id, this.searchText[c.id]).subscribe({
      next: (f) => this.files.update((m) => ({ ...m, [c.id]: f })),
      error: () => {},
    });
  }
}
