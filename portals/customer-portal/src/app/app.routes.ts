import { Routes } from '@angular/router';
import { authGuard } from './core/auth.guard';
import { ShellComponent } from './layout/shell.component';

export const routes: Routes = [
  { path: 'signin', loadComponent: () => import('./pages/signin.component').then((m) => m.SigninComponent) },
  { path: 'signup', loadComponent: () => import('./pages/signup.component').then((m) => m.SignupComponent) },
  { path: 'forgot-password', loadComponent: () => import('./pages/forgot-password.component').then((m) => m.ForgotPasswordComponent) },
  { path: 'reset-password', loadComponent: () => import('./pages/reset-password.component').then((m) => m.ResetPasswordComponent) },
  { path: 'verify-email', loadComponent: () => import('./pages/verify-email.component').then((m) => m.VerifyEmailComponent) },
  {
    path: '',
    component: ShellComponent,
    canActivate: [authGuard],
    children: [
      { path: '', pathMatch: 'full', redirectTo: 'dashboard' },
      { path: 'dashboard', loadComponent: () => import('./pages/dashboard.component').then((m) => m.DashboardComponent) },
      { path: 'connections', loadComponent: () => import('./pages/connections.component').then((m) => m.ConnectionsComponent) },
      { path: 'projects', loadComponent: () => import('./pages/projects.component').then((m) => m.ProjectsComponent) },
      { path: 'knowledge-bank', loadComponent: () => import('./pages/knowledge-bank.component').then((m) => m.KnowledgeBankComponent) },
      { path: 'prompts', loadComponent: () => import('./pages/prompts.component').then((m) => m.PromptsComponent) },
      { path: 'preferences', loadComponent: () => import('./pages/preferences.component').then((m) => m.PreferencesComponent) },
      { path: 'payment-settings', loadComponent: () => import('./pages/payment-settings.component').then((m) => m.PaymentSettingsComponent) },
      { path: 'billing', loadComponent: () => import('./pages/billing.component').then((m) => m.BillingComponent) },
      { path: 'activity', loadComponent: () => import('./pages/activity.component').then((m) => m.ActivityComponent) },
    ],
  },
  { path: '**', redirectTo: '' },
];
