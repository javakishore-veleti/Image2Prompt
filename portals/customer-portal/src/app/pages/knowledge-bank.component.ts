import { Component, computed, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService, KbGroup, KbResult, ProjectKb, PromptItem } from '../core/api.service';

@Component({
  selector: 'app-knowledge-bank',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <h2 class="page-title">Project Knowledge Bank</h2>
    <p class="muted">
      Build a per-project knowledge base from your generated prompts. Pick a vector-store
      tech stack (allowed by your subscription), then ingest the prompts you choose and search them.
    </p>

    <div class="card sub" *ngIf="sub() as s">
      <ng-container *ngIf="s.has_subscription; else noSub">
        <strong>{{ s.plan_name }}</strong> plan ·
        stacks: <span class="mono">{{ s.stacks.join(', ') }}</span>
        <span *ngIf="s.max_kbs != null"> · up to {{ s.max_kbs }} KBs</span>
        <span *ngIf="s.max_docs_per_kb != null"> · {{ s.max_docs_per_kb }} docs/KB</span>
      </ng-container>
      <ng-template #noSub>
        <span class="muted" *ngIf="s.gating_enabled">No active subscription — ask an admin to assign a plan to create KBs.</span>
        <span class="muted" *ngIf="!s.gating_enabled">Subscription gating is off (dev): all tech stacks available.</span>
      </ng-template>
    </div>

    <div class="card">
      <div class="field">
        <label>Project</label>
        <select [(ngModel)]="projectId" (change)="onProject()">
          <option value="">— select a project —</option>
          <option *ngFor="let p of projects()" [value]="p.id">{{ p.name }}</option>
        </select>
      </div>
    </div>

    <div class="grid" *ngIf="projectId">
      <!-- Groups + KBs -->
      <div class="card">
        <h3>KB Groups</h3>
        <div class="row">
          <input placeholder="New group name" [(ngModel)]="groupName" />
          <button (click)="createGroup()" [disabled]="!groupName.trim()">Add</button>
        </div>
        <div class="list">
          <button class="item" *ngFor="let g of groups()" [class.active]="group()?.id === g.id" (click)="selectGroup(g)">
            {{ g.name }}
          </button>
          <p class="muted" *ngIf="groups().length === 0">No groups yet.</p>
        </div>

        <div *ngIf="group()">
          <div class="hrow">
            <h3>KBs in “{{ group()?.name }}”</h3>
            <button class="danger small" (click)="deleteGroup()">Delete group</button>
          </div>
          <div class="row">
            <input placeholder="New KB name" [(ngModel)]="kbName" />
            <select [(ngModel)]="kbStack">
              <option value="">tech stack…</option>
              <option *ngFor="let s of stacks()" [value]="s">{{ s }}</option>
            </select>
            <button (click)="createKb()" [disabled]="!kbName.trim() || !kbStack">Add</button>
          </div>
          <p class="error" *ngIf="error()">{{ error() }}</p>
          <div class="list">
            <button class="item" *ngFor="let k of kbs()" [class.active]="kb()?.id === k.id" (click)="selectKb(k)">
              {{ k.name }} <span class="chip mono">{{ k.tech_stack }}</span>
              <span class="muted small">· {{ k.doc_count }} docs{{ k.backend_ready ? '' : ' · in-memory' }}</span>
            </button>
            <p class="muted" *ngIf="kbs().length === 0">No KBs yet.</p>
          </div>
        </div>
      </div>

      <!-- Selected KB: ingest + search -->
      <div class="card" *ngIf="kb() as k">
        <div class="hrow">
          <h3>{{ k.name }} <span class="chip mono">{{ k.tech_stack }}</span></h3>
          <button class="danger small" (click)="deleteKb()">Delete KB</button>
        </div>

        <h4>Ingest prompts</h4>
        <p class="muted small">Select generated prompts to add to this KB.</p>
        <div class="prompts">
          <label class="prow" *ngFor="let p of uniquePrompts()">
            <input type="checkbox" [checked]="selected.has(p.request_id)" (change)="toggle(p.request_id)" />
            <span class="ptext">{{ p.output_text }}</span>
          </label>
          <p class="muted" *ngIf="uniquePrompts().length === 0">No prompts yet — generate some first.</p>
        </div>
        <div class="row">
          <button (click)="ingest()" [disabled]="selected.size === 0 || busy()">
            {{ busy() ? 'Ingesting…' : 'Ingest ' + selected.size + ' selected' }}
          </button>
          <button class="ghost" (click)="ingestAsync()" [disabled]="selected.size === 0 || busy()">
            Ingest in background
          </button>
        </div>
        <span class="ok small" *ngIf="ingestMsg()">{{ ingestMsg() }}</span>

        <h4>Search this KB</h4>
        <div class="row">
          <input placeholder="Search the knowledge bank…" [(ngModel)]="q" (keyup.enter)="search()" />
          <button (click)="search()" [disabled]="!q.trim()">Search</button>
        </div>
        <div class="results">
          <div class="res" *ngFor="let r of results()">
            <span class="score">{{ (r.score * 100) | number: '1.0-0' }}%</span>
            <span class="rtext">{{ r.title }}</span>
          </div>
          <p class="muted" *ngIf="searched() && results().length === 0">No matches.</p>
        </div>
      </div>
    </div>
  `,
  styles: [
    `
      .sub { font-size: 13px; }
      .hrow { display: flex; align-items: center; justify-content: space-between; gap: 10px; }
      .danger { background: transparent; color: #c0392b; border: 1px solid #c0392b; border-radius: 8px; padding: 4px 10px; }
      .danger:hover { background: #c0392b; color: #fff; }
      .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
      @media (max-width: 900px) { .grid { grid-template-columns: 1fr; } }
      .row { display: flex; gap: 8px; margin-bottom: 10px; flex-wrap: wrap; }
      .list { display: flex; flex-direction: column; gap: 6px; margin-bottom: 14px; }
      .item { text-align: left; background: var(--panel-2); border: 1px solid var(--border); border-radius: 8px; padding: 8px 10px; }
      .item.active { border-color: var(--brand); color: var(--brand); }
      .chip { background: var(--panel-2); border-radius: 999px; padding: 1px 8px; font-size: 11px; }
      .mono { font-family: monospace; }
      .small { font-size: 12px; }
      h4 { margin: 14px 0 6px; }
      .prompts { max-height: 220px; overflow: auto; border: 1px solid var(--border); border-radius: 8px; padding: 8px; margin-bottom: 8px; }
      .prow { display: flex; gap: 8px; padding: 4px 0; align-items: flex-start; }
      .ptext { font-size: 13px; }
      .results { margin-top: 8px; }
      .res { display: flex; gap: 10px; padding: 6px 0; border-bottom: 1px solid var(--border); }
      .score { font-weight: 700; color: var(--brand); min-width: 48px; }
      .rtext { font-size: 13px; }
    `,
  ],
})
export class KnowledgeBankComponent {
  private api = inject(ApiService);

  projects = signal<{ id: string; name: string }[]>([]);
  stacks = signal<string[]>([]);
  sub = signal<{
    has_subscription: boolean;
    plan_name: string | null;
    stacks: string[];
    max_kbs: number | null;
    max_docs_per_kb: number | null;
    gating_enabled: boolean;
  } | null>(null);
  groups = signal<KbGroup[]>([]);
  group = signal<KbGroup | null>(null);
  kbs = signal<ProjectKb[]>([]);
  kb = signal<ProjectKb | null>(null);
  prompts = signal<PromptItem[]>([]);
  results = signal<KbResult[]>([]);
  searched = signal(false);
  busy = signal(false);
  error = signal('');
  ingestMsg = signal('');

  projectId = '';
  groupName = '';
  kbName = '';
  kbStack = '';
  q = '';
  selected = new Set<string>();

  uniquePrompts = computed(() => {
    const seen = new Set<string>();
    return this.prompts().filter((p) => (seen.has(p.request_id) ? false : seen.add(p.request_id)));
  });

  constructor() {
    this.api.projects().subscribe({ next: (p) => this.projects.set(p), error: () => {} });
    this.api.myKbSubscription().subscribe({
      next: (s) => {
        this.sub.set(s);
        this.stacks.set(s.stacks ?? []);
      },
      error: () => {
        // fall back to the full catalog if the subscription lookup is unavailable
        this.api.kbTechStacks().subscribe({ next: (st) => this.stacks.set(st), error: () => {} });
      },
    });
  }

  onProject(): void {
    this.group.set(null);
    this.kb.set(null);
    this.kbs.set([]);
    this.results.set([]);
    if (!this.projectId) return;
    this.api.kbGroups(this.projectId).subscribe({ next: (g) => this.groups.set(g), error: () => {} });
    this.api.prompts().subscribe({ next: (p) => this.prompts.set(p), error: () => {} });
  }

  createGroup(): void {
    this.api.createKbGroup(this.projectId, this.groupName.trim()).subscribe({
      next: () => {
        this.groupName = '';
        this.api.kbGroups(this.projectId).subscribe({ next: (g) => this.groups.set(g) });
      },
      error: () => {},
    });
  }

  selectGroup(g: KbGroup): void {
    this.group.set(g);
    this.kb.set(null);
    this.api.kbs(g.id).subscribe({ next: (k) => this.kbs.set(k), error: () => {} });
  }

  createKb(): void {
    this.error.set('');
    const g = this.group();
    if (!g) return;
    this.api
      .createKb({ group_id: g.id, project_id: this.projectId, name: this.kbName.trim(), tech_stack: this.kbStack })
      .subscribe({
        next: () => {
          this.kbName = '';
          this.kbStack = '';
          this.selectGroup(g);
        },
        error: (err) => this.error.set(err?.error?.detail ?? 'Create failed (check your subscription)'),
      });
  }

  deleteGroup(): void {
    const g = this.group();
    if (!g || !confirm(`Delete group “${g.name}” and all its KBs? This cannot be undone.`)) return;
    this.api.deleteKbGroup(g.id).subscribe({
      next: () => {
        this.group.set(null);
        this.kb.set(null);
        this.kbs.set([]);
        this.api.kbGroups(this.projectId).subscribe({ next: (gs) => this.groups.set(gs) });
      },
      error: () => {},
    });
  }

  deleteKb(): void {
    const k = this.kb();
    const g = this.group();
    if (!k || !g || !confirm(`Delete KB “${k.name}”? Its documents and vectors will be removed.`)) return;
    this.api.deleteKb(k.id).subscribe({
      next: () => {
        this.kb.set(null);
        this.selectGroup(g);
      },
      error: () => {},
    });
  }

  selectKb(k: ProjectKb): void {
    this.kb.set(k);
    this.results.set([]);
    this.searched.set(false);
    this.ingestMsg.set('');
    this.selected.clear();
  }

  toggle(id: string): void {
    if (this.selected.has(id)) this.selected.delete(id);
    else this.selected.add(id);
  }

  ingest(): void {
    const k = this.kb();
    if (!k || this.selected.size === 0) return;
    this.busy.set(true);
    this.api.ingestKb(k.id, Array.from(this.selected)).subscribe({
      next: (r) => {
        this.busy.set(false);
        this.ingestMsg.set(`Ingested ${r.ingested}, skipped ${r.skipped}. Total ${r.doc_count}.`);
        this.selected.clear();
        this.api.kbs(this.group()!.id).subscribe({ next: (kbs) => {
          this.kbs.set(kbs);
          this.kb.set(kbs.find((x) => x.id === k.id) ?? k);
        } });
      },
      error: () => {
        this.busy.set(false);
        this.ingestMsg.set('Ingest failed.');
      },
    });
  }

  ingestAsync(): void {
    const k = this.kb();
    if (!k || this.selected.size === 0) return;
    this.busy.set(true);
    this.ingestMsg.set('Queued…');
    this.api.ingestKbAsync(k.id, Array.from(this.selected)).subscribe({
      next: (job) => {
        this.selected.clear();
        this.pollJob(k.id, job.id);
      },
      error: () => {
        this.busy.set(false);
        this.ingestMsg.set('Ingest failed.');
      },
    });
  }

  private pollJob(kbId: string, jobId: string): void {
    this.api.ingestJob(kbId, jobId).subscribe({
      next: (job) => {
        if (job.status === 'done') {
          this.busy.set(false);
          this.ingestMsg.set(`Background ingest done: ${job.ingested} added, ${job.skipped} skipped.`);
          this.refreshKbs(kbId);
        } else if (job.status === 'error') {
          this.busy.set(false);
          this.ingestMsg.set('Background ingest failed: ' + (job.error ?? ''));
        } else {
          this.ingestMsg.set(`Background ingest ${job.status}…`);
          setTimeout(() => this.pollJob(kbId, jobId), 1500);
        }
      },
      error: () => {
        this.busy.set(false);
        this.ingestMsg.set('Lost track of the background job.');
      },
    });
  }

  private refreshKbs(kbId: string): void {
    const g = this.group();
    if (!g) return;
    this.api.kbs(g.id).subscribe({
      next: (kbs) => {
        this.kbs.set(kbs);
        const cur = this.kb();
        if (cur) this.kb.set(kbs.find((x) => x.id === kbId) ?? cur);
      },
    });
  }

  search(): void {
    const k = this.kb();
    if (!k || !this.q.trim()) return;
    this.api.queryKb(k.id, this.q.trim()).subscribe({
      next: (r) => {
        this.results.set(r.results);
        this.searched.set(true);
      },
      error: () => {},
    });
  }
}
