import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { AuthService } from '../core/auth.service';

interface NavItem {
  label: string;
  link?: string;
  disabled?: boolean;
}

@Component({
  selector: 'app-shell',
  standalone: true,
  imports: [CommonModule, RouterLink, RouterLinkActive, RouterOutlet],
  template: `
    <div class="layout">
      <aside class="sidebar">
        <div class="brand">Image<span>2</span>Prompt</div>
        <nav>
          <ng-container *ngFor="let item of nav">
            <a
              *ngIf="!item.disabled"
              [routerLink]="item.link"
              routerLinkActive="active"
              class="nav-item"
              >{{ item.label }}</a
            >
            <span *ngIf="item.disabled" class="nav-item disabled" title="Coming soon">
              {{ item.label }} <em>soon</em>
            </span>
          </ng-container>
        </nav>
        <button class="signout ghost" (click)="signout()">Sign out</button>
      </aside>
      <main class="content">
        <header class="topbar">
          <span class="muted">Signed in as</span>&nbsp;<strong>{{ auth.email() }}</strong>
        </header>
        <section class="content-body">
          <router-outlet></router-outlet>
        </section>
      </main>
    </div>
  `,
  styles: [
    `
      .layout { display: flex; min-height: 100vh; }
      .sidebar {
        width: 240px;
        background: #ffffff;
        border-right: 1px solid var(--border);
        display: flex;
        flex-direction: column;
        padding: 20px 14px;
      }
      .brand { font-size: 20px; font-weight: 800; margin-bottom: 24px; padding: 0 8px; }
      .brand span { color: var(--brand); }
      nav { display: flex; flex-direction: column; gap: 4px; flex: 1; }
      .nav-item {
        display: block;
        padding: 10px 12px;
        border-radius: 10px;
        color: var(--muted);
        font-weight: 600;
      }
      .nav-item:hover { background: var(--panel-2); color: var(--text); }
      .nav-item.active { background: var(--bg-accent); color: var(--brand); }
      .nav-item.disabled { color: #aab2c2; cursor: not-allowed; }
      .nav-item.disabled em { font-size: 10px; opacity: 0.7; }
      .signout { margin-top: 12px; }
      .content { flex: 1; display: flex; flex-direction: column; }
      .topbar {
        padding: 16px 28px;
        border-bottom: 1px solid var(--border);
        background: rgba(255, 255, 255, 0.7);
        font-size: 14px;
      }
      .content-body { padding: 28px; max-width: 1000px; }
    `,
  ],
})
export class ShellComponent {
  auth = inject(AuthService);
  private router = inject(Router);

  nav: NavItem[] = [
    { label: 'Dashboard', link: '/dashboard' },
    { label: 'Connections', disabled: true },
    { label: 'Projects', link: '/projects' },
    { label: 'Prompts', link: '/prompts' },
    { label: 'Preferences', link: '/preferences' },
    { label: 'Payment Settings', link: '/payment-settings' },
    { label: 'Billing & Receipts', link: '/billing' },
  ];

  signout(): void {
    this.auth.logout();
    this.router.navigateByUrl('/signin');
  }
}
