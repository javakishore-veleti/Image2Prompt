import { Component } from '@angular/core';

@Component({
  selector: 'app-customer-endpoints',
  standalone: true,
  template: `
    <h2 class="page-title">Customer Endpoints</h2>
    <div class="card">
      <p class="muted">
        This page will list each customer's connected file systems — Google Drive,
        OneDrive, S3, and others — with search-by-customer. Cloud connections are not
        yet wired in this build (customers currently upload images directly).
      </p>
    </div>
  `,
})
export class CustomerEndpointsComponent {}
