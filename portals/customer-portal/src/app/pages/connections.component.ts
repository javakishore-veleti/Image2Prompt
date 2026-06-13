import { Component } from '@angular/core';

@Component({
  selector: 'app-connections',
  standalone: true,
  template: `
    <h2 class="page-title">Connections</h2>
    <div class="card">
      <p class="muted">
        Cloud storage connections (Google Drive, OneDrive, S3, and others) are coming soon.
        For now, upload images directly from the Dashboard.
      </p>
    </div>
  `,
})
export class ConnectionsComponent {}
