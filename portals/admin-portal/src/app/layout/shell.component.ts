import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { AuthService } from '../core/auth.service';

interface NavItem {
  label: string;
  link: string;
  exact?: boolean;
}

@Component({
  selector: 'app-shell',
  standalone: true,
  imports: [CommonModule, RouterLink, RouterLinkActive, RouterOutlet],
  template: `
    <div class="layout">
      <aside class="sidebar">
        <div class="brand">Image<span>2</span>Prompt <em>Admin</em></div>
        <nav>
          <a
            *ngFor="let item of nav"
            [routerLink]="item.link"
            routerLinkActive="active"
            [routerLinkActiveOptions]="{ exact: !!item.exact }"
            class="nav-item"
            >{{ item.label }}</a
          >
        </nav>
        <button class="signout ghost" (click)="signout()">Sign out</button>
      </aside>
      <main class="content">
        <header class="topbar">
          <span class="muted">Admin</span>&nbsp;<strong>{{ auth.email() }}</strong>
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
        width: 240px; background: var(--navy);
        display: flex; flex-direction: column; padding: 20px 14px;
      }
      .brand { font-size: 18px; font-weight: 800; color: #fff; margin-bottom: 24px; padding: 0 8px; }
      .brand span { color: #6ea8fe; }
      .brand em { color: #9fb3d1; font-style: normal; font-size: 12px; }
      nav { display: flex; flex-direction: column; gap: 4px; flex: 1; }
      .nav-item { display: block; padding: 10px 12px; border-radius: 8px; color: #c4d2e8; font-weight: 600; }
      .nav-item:hover { background: var(--navy-2); color: #fff; }
      .nav-item.active { background: var(--brand); color: #fff; }
      .signout { margin-top: 12px; background: transparent; border: 1px solid var(--navy-2); color: #c4d2e8; }
      .signout:hover { background: var(--navy-2); color: #fff; }
      .content { flex: 1; display: flex; flex-direction: column; background: var(--bg); }
      .topbar { padding: 16px 28px; border-bottom: 1px solid var(--border); background: #fff; font-size: 14px; }
      .content-body { padding: 28px; max-width: 1100px; }
    `,
  ],
})
export class ShellComponent {
  auth = inject(AuthService);
  private router = inject(Router);

  get nav(): NavItem[] {
    const items: NavItem[] = [
      { label: 'Dashboard', link: '/dashboard' },
      { label: 'Customer Search', link: '/customers/search' },
      { label: 'Customer Listing', link: '/customers', exact: true },
      { label: 'Customer Endpoints', link: '/customers/endpoints' },
      { label: 'Providers', link: '/providers' },
    ];
    if (this.auth.isSuperadmin) {
      items.push({ label: 'Admins', link: '/admins' });
    }
    return items;
  }

  signout(): void {
    this.auth.logout();
    this.router.navigateByUrl('/signin');
  }
}
