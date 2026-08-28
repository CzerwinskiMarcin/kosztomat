import { ChangeDetectionStrategy, Component, inject, OnInit, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { firstValueFrom } from 'rxjs';

import { FilesApi } from '../../core/files.api';
import { ProfilesApi } from '../../core/profiles.api';
import {
  ImportErrorItem,
  Preview,
  SourceFile,
  SourceProfile,
  TransactionRow,
} from '../../core/models';
import { DatePlPipe } from '../../shared/date-pl.pipe';
import { PlnPipe } from '../../shared/pln.pipe';

@Component({
  selector: 'app-file-detail',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    FormsModule,
    RouterLink,
    MatButtonModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatCheckboxModule,
    MatSnackBarModule,
    DatePlPipe,
    PlnPipe,
  ],
  templateUrl: './file-detail.component.html',
  styleUrl: './file-detail.component.scss',
})
export class FileDetailComponent implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly filesApi = inject(FilesApi);
  private readonly profilesApi = inject(ProfilesApi);
  private readonly snackBar = inject(MatSnackBar);

  readonly file = signal<SourceFile | null>(null);
  readonly profiles = signal<SourceProfile[]>([]);
  readonly preview = signal<Preview | null>(null);
  readonly transactions = signal<TransactionRow[]>([]);
  readonly importing = signal(false);
  readonly wizardMode = signal(false);
  readonly errors = signal<ImportErrorItem[]>([]);

  selectedProfileId: number | 'new' = 'new';
  encoding = 'utf-8-sig';
  delimiter = ';';
  skipRows = 0;
  hasHeader = true;
  decimalSeparator = ',';
  thousandSeparator = ' ';
  dateFormat = '%d.%m.%Y';
  amountMode: 'signed' | 'absolute' = 'signed';
  dateColumn = '';
  amountColumn = '';
  descriptionColumn = '';
  saveProfileName = '';

  async ngOnInit(): Promise<void> {
    const id = Number(this.route.snapshot.paramMap.get('id'));
    const [file, profiles] = await Promise.all([
      firstValueFrom(this.filesApi.get(id)),
      firstValueFrom(this.profilesApi.list()),
    ]);
    this.file.set(file);
    this.profiles.set(profiles);
    this.wizardMode.set(file.status !== 'imported');
    if (file.status === 'imported') {
      const page = await firstValueFrom(this.filesApi.transactions(id, 0, 100));
      this.transactions.set(page.items);
    } else {
      await this.loadPreview();
    }
  }

  async onProfileChange(): Promise<void> {
    if (this.selectedProfileId === 'new') {
      return;
    }
    const profile = this.profiles().find((item) => item.id === this.selectedProfileId);
    if (!profile) {
      return;
    }
    this.encoding = profile.encoding;
    this.delimiter = profile.delimiter;
    this.skipRows = profile.skip_rows;
    this.hasHeader = profile.has_header;
    this.decimalSeparator = profile.decimal_separator;
    this.thousandSeparator = profile.thousand_separator;
    this.dateFormat = profile.date_format;
    this.amountMode = profile.amount_mode;
    this.dateColumn = String(profile.column_mapping.booking_date ?? '');
    this.amountColumn = String(profile.column_mapping.amount ?? '');
    this.descriptionColumn = String(profile.column_mapping.description ?? '');
    await this.loadPreview();
  }

  async loadPreview(): Promise<void> {
    const file = this.file();
    if (!file) {
      return;
    }
    const preview = await firstValueFrom(
      this.filesApi.preview(file.id, {
        encoding: this.encoding,
        delimiter: this.delimiter,
        skip_rows: this.skipRows,
        has_header: this.hasHeader,
      }),
    );
    this.preview.set(preview);
    this.encoding = preview.encoding;
    this.delimiter = preview.delimiter;
    if (!this.dateColumn && preview.headers.length) {
      this.guessColumns(preview.headers);
    }
  }

  async importNow(): Promise<void> {
    const file = this.file();
    if (!file) {
      return;
    }
    this.importing.set(true);
    this.errors.set([]);
    try {
      const usingProfile =
        this.selectedProfileId !== 'new' ? Number(this.selectedProfileId) : null;
      const result = await firstValueFrom(
        this.filesApi.importFile(file.id, {
          profile_id: usingProfile,
          config: usingProfile
            ? undefined
            : {
                name: this.saveProfileName || file.display_name,
                delimiter: this.delimiter,
                encoding: this.encoding,
                has_header: this.hasHeader,
                skip_rows: this.skipRows,
                decimal_separator: this.decimalSeparator,
                thousand_separator: this.thousandSeparator,
                date_format: this.dateFormat,
                amount_mode: this.amountMode,
                column_mapping: {
                  booking_date: this.dateColumn,
                  amount: this.amountColumn,
                  description: this.descriptionColumn || null,
                },
              },
          save_as_profile:
            !usingProfile && this.saveProfileName
              ? { name: this.saveProfileName }
              : null,
        }),
      );
      if (result.errors.length) {
        this.errors.set(result.errors);
        this.file.set(result.file);
        return;
      }
      this.file.set(result.file);
      this.wizardMode.set(false);
      const page = await firstValueFrom(this.filesApi.transactions(file.id, 0, 100));
      this.transactions.set(page.items);
    } catch {
      this.snackBar.open('Import się nie powiódł. Sprawdź mapowanie kolumn i format daty.', 'OK');
    } finally {
      this.importing.set(false);
    }
  }

  reimport(): void {
    this.wizardMode.set(true);
    void this.loadPreview();
  }

  async deleteFile(): Promise<void> {
    const file = this.file();
    if (!file) {
      return;
    }
    if (!confirm(`Usunąć plik „${file.display_name}”? Tej operacji nie da się cofnąć.`)) {
      return;
    }
    await firstValueFrom(this.filesApi.delete(file.id));
    await this.router.navigate(['/files']);
  }

  trackByTx = (_index: number, row: TransactionRow): number => row.id;

  private guessColumns(headers: string[]): void {
    const lower = headers.map((item) => item.toLowerCase());
    const find = (...needles: string[]): string => {
      const index = lower.findIndex((header) => needles.some((needle) => header.includes(needle)));
      return index >= 0 ? headers[index] : headers[0] ?? '';
    };
    this.dateColumn = find('data', 'date');
    this.amountColumn = find('kwota', 'amount');
    this.descriptionColumn = find('opis', 'tytuł', 'title', 'description');
  }
}
