import { ChangeDetectionStrategy, Component, computed, inject, OnInit, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatButtonToggleModule } from '@angular/material/button-toggle';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { firstValueFrom } from 'rxjs';

import { ComparisonsApi } from '../../core/comparisons.api';
import { Comparison, MatchKind, MatchRow } from '../../core/models';
import { DatePlPipe } from '../../shared/date-pl.pipe';
import { PlnPipe } from '../../shared/pln.pipe';

@Component({
  selector: 'app-compare-result',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    FormsModule,
    MatButtonModule,
    MatButtonToggleModule,
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
  readonly kind = signal<MatchKind>('exact');
  readonly query = signal('');
  readonly amountFilter = signal('');
  readonly loading = signal(true);

  readonly visible = computed(() => {
    const kind = this.kind();
    const query = this.query().trim().toLowerCase();
    const amount = this.amountFilter().trim().replace(',', '.');
    return this.matches().filter((row) => {
      if (row.kind !== kind) {
        return false;
      }
      if (amount && row.amount !== Number(amount).toFixed(2)) {
        return false;
      }
      if (!query) {
        return true;
      }
      const haystack = `${row.a?.description ?? ''} ${row.b?.description ?? ''}`.toLowerCase();
      return haystack.includes(query);
    });
  });

  async ngOnInit(): Promise<void> {
    await this.load(Number(this.route.snapshot.paramMap.get('id')));
  }

  setKind(kind: MatchKind): void {
    this.kind.set(kind);
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
