import { ChangeDetectionStrategy, Component, computed, inject, OnInit, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { firstValueFrom } from 'rxjs';

import { ComparisonsApi } from '../../core/comparisons.api';
import { Comparison, MatchRow } from '../../core/models';
import { DatePlPipe } from '../../shared/date-pl.pipe';
import { PlnPipe } from '../../shared/pln.pipe';

export type ResultView = 'unmatched' | 'probable' | 'exact';
export type UnmatchedSource = 'all' | 'a' | 'b';

@Component({
  selector: 'app-compare-result',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    FormsModule,
    RouterLink,
    MatButtonModule,
    MatFormFieldModule,
    MatInputModule,
    DatePlPipe,
    PlnPipe,
  ],
  templateUrl: './compare-result.component.html',
  styleUrl: './compare-result.component.scss',
})
export class CompareResultComponent implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly comparisonsApi = inject(ComparisonsApi);

  readonly comparison = signal<Comparison | null>(null);
  readonly matches = signal<MatchRow[]>([]);
  readonly view = signal<ResultView>('unmatched');
  readonly unmatchedSource = signal<UnmatchedSource>('all');
  readonly query = signal('');
  readonly amountFilter = signal('');
  readonly loading = signal(true);

  readonly unmatchedEmptyMessage = computed(() => {
    const current = this.comparison();
    if (!current) {
      return 'Brak wierszy.';
    }
    const source = this.unmatchedSource();
    if (source === 'a') {
      return `Brak wpisów z „${this.fileLabel(current.file_a.display_name)}”, których nie ma w „${this.fileLabel(current.file_b.display_name)}”.`;
    }
    if (source === 'b') {
      return `Brak wpisów z „${this.fileLabel(current.file_b.display_name)}”, których nie ma w „${this.fileLabel(current.file_a.display_name)}”.`;
    }
    return 'Wszystkie wpisy mają odpowiednik w drugim pliku.';
  });

  readonly unmatchedCount = computed(() => {
    const summary = this.comparison()?.summary;
    if (!summary) {
      return 0;
    }
    return summary.unmatched_a + summary.unmatched_b;
  });

  readonly unmatchedSum = computed(() => this.sumByKind(['unmatched_a', 'unmatched_b']));
  readonly unmatchedSumA = computed(() => this.sumByKind(['unmatched_a']));
  readonly unmatchedSumB = computed(() => this.sumByKind(['unmatched_b']));
  readonly visibleSum = computed(() => this.sumRows(this.visible()));

  readonly visible = computed(() => {
    const view = this.view();
    const unmatchedSource = this.unmatchedSource();
    const query = this.query().trim().toLowerCase();
    const amountRaw = this.amountFilter().trim().replace(',', '.');
    const amount = amountRaw ? Number(amountRaw).toFixed(2) : '';

    const rows = this.matches().filter((row) => {
      const inView =
        view === 'unmatched'
          ? unmatchedSource === 'a'
            ? row.kind === 'unmatched_a'
            : unmatchedSource === 'b'
              ? row.kind === 'unmatched_b'
              : row.kind === 'unmatched_a' || row.kind === 'unmatched_b'
          : view === 'probable'
            ? row.kind === 'probable'
            : row.kind === 'exact';
      if (!inView) {
        return false;
      }
      if (amount && row.amount !== amount) {
        return false;
      }
      if (!query) {
        return true;
      }
      const haystack = `${row.a?.description ?? ''} ${row.b?.description ?? ''}`.toLowerCase();
      return haystack.includes(query);
    });

    return rows.slice().sort((left, right) => {
      const dateLeft = (left.a?.booking_date ?? left.b?.booking_date ?? '').slice(0, 10);
      const dateRight = (right.a?.booking_date ?? right.b?.booking_date ?? '').slice(0, 10);
      if (dateLeft !== dateRight) {
        return dateLeft.localeCompare(dateRight);
      }
      return left.amount.localeCompare(right.amount);
    });
  });

  async ngOnInit(): Promise<void> {
    await this.load(Number(this.route.snapshot.paramMap.get('id')));
  }

  setView(view: ResultView): void {
    this.view.set(view);
  }

  showUnmatched(source: UnmatchedSource = 'all'): void {
    this.unmatchedSource.set(source);
    this.view.set('unmatched');
  }

  fileLabel(name: string): string {
    return name.replace(/\.(csv|txt)$/i, '');
  }

  presentIn(row: MatchRow): string {
    const current = this.comparison();
    if (!current) {
      return '';
    }
    return row.kind === 'unmatched_b'
      ? this.fileLabel(current.file_b.display_name)
      : this.fileLabel(current.file_a.display_name);
  }

  missingFrom(row: MatchRow): string {
    const current = this.comparison();
    if (!current) {
      return '';
    }
    return row.kind === 'unmatched_b'
      ? this.fileLabel(current.file_a.display_name)
      : this.fileLabel(current.file_b.display_name);
  }

  side(row: MatchRow): MatchRow['a'] {
    return row.a ?? row.b;
  }

  async rerun(): Promise<void> {
    const current = this.comparison();
    if (!current) {
      return;
    }
    this.loading.set(true);
    const result = await firstValueFrom(
      this.comparisonsApi.create(
        current.file_a.id,
        current.file_b.id,
        current.date_tolerance_days,
      ),
    );
    await this.router.navigate(['/compare', result.id], { replaceUrl: true });
    await this.load(result.id);
  }

  trackByMatch = (_index: number, row: MatchRow): number => row.id;

  private sumByKind(kinds: MatchRow['kind'][]): string {
    return this.sumRows(this.matches().filter((row) => kinds.includes(row.kind)));
  }

  private sumRows(rows: MatchRow[]): string {
    const cents = rows.reduce((total, row) => total + Math.round(Number(row.amount) * 100), 0);
    return (cents / 100).toFixed(2);
  }

  private async load(id: number): Promise<void> {
    const [comparison, matches] = await Promise.all([
      firstValueFrom(this.comparisonsApi.get(id)),
      firstValueFrom(this.comparisonsApi.matches(id)),
    ]);
    this.comparison.set(comparison);
    this.matches.set(matches);
    this.loading.set(false);
  }
}
