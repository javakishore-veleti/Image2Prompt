import { Routes } from '@angular/router';
import { authGuard } from './core/auth.guard';
import { ShellComponent } from './layout/shell.component';

export const routes: Routes = [
  { path: 'signin', loadComponent: () => import('./pages/signin.component').then((m) => m.SigninComponent) },
  { path: 'signup', loadComponent: () => import('./pages/signup.component').then((m) => m.SignupComponent) },
  {
    path: '',
    component: ShellComponent,
    canActivate: [authGuard],
    children: [
      { path: '', pathMatch: 'full', redirectTo: 'dashboard' },
      { path: 'dashboard', loadComponent: () => import('./pages/dashboard.component').then((m) => m.DashboardComponent) },
      { path: 'connections', loadComponent: () => import('./pages/connections.component').then((m) => m.ConnectionsComponent) },
      { path: 'projects', loadComponent: () => import('./pages/projects.component').then((m) => m.ProjectsComponent) },
      { path: 'prompts', loadComponent: () => import('./pages/prompts.component').then((m) => m.PromptsComponent) },
      { path: 'payment-settings', loadComponent: () => import('./pages/payment-settings.component').then((m) => m.PaymentSettingsComponent) },
      { path: 'billing', loadComponent: () => import('./pages/billing.component').then((m) => m.BillingComponent) },
    ],
  },
  { path: '**', redirectTo: '' },
];
