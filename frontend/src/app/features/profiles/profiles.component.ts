import { ChangeDetectionStrategy, Component, inject, OnInit, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { firstValueFrom } from 'rxjs';

import { ProfilePayload, SourceProfile } from '../../core/models';
import { ProfilesApi } from '../../core/profiles.api';
import { EmptyStateComponent } from '../../shared/empty-state.component';

@Component({
  selector: 'app-profiles',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    FormsModule,
    MatButtonModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatSnackBarModule,
    EmptyStateComponent,
  ],
  templateUrl: './profiles.component.html',
  styleUrl: './profiles.component.scss',
})
export class ProfilesComponent implements OnInit {
  private readonly profilesApi = inject(ProfilesApi);
  private readonly snackBar = inject(MatSnackBar);

  readonly profiles = signal<SourceProfile[]>([]);
  readonly editingId = signal<number | null>(null);

  name = '';
  delimiter = ';';
  encoding = 'utf-8-sig';
  dateFormat = '%d.%m.%Y';
  decimalSeparator = ',';
  amountMode: 'signed' | 'absolute' = 'signed';
  dateColumn = 'Data';
  amountColumn = 'Kwota';
  descriptionColumn = 'Opis';

  async ngOnInit(): Promise<void> {
    await this.reload();
  }

  edit(profile: SourceProfile): void {
    this.editingId.set(profile.id);
    this.name = profile.name;
    this.delimiter = profile.delimiter;
    this.encoding = profile.encoding;
    this.dateFormat = profile.date_format;
    this.decimalSeparator = profile.decimal_separator;
    this.amountMode = profile.amount_mode;
    this.dateColumn = String(profile.column_mapping.booking_date ?? '');
    this.amountColumn = String(profile.column_mapping.amount ?? '');
    this.descriptionColumn = String(profile.column_mapping.description ?? '');
  }

  resetForm(): void {
    this.editingId.set(null);
    this.name = '';
    this.delimiter = ';';
    this.encoding = 'utf-8-sig';
    this.dateFormat = '%d.%m.%Y';
    this.decimalSeparator = ',';
    this.amountMode = 'signed';
    this.dateColumn = 'Data';
    this.amountColumn = 'Kwota';
    this.descriptionColumn = 'Opis';
  }

  async save(): Promise<void> {
    const payload: ProfilePayload = {
      name: this.name,
      delimiter: this.delimiter,
      encoding: this.encoding,
      has_header: true,
      skip_rows: 0,
      decimal_separator: this.decimalSeparator,
      thousand_separator: ' ',
      date_format: this.dateFormat,
      amount_mode: this.amountMode,
      column_mapping: {
        booking_date: this.dateColumn,
        amount: this.amountColumn,
        description: this.descriptionColumn || null,
      },
    };
    try {
      const id = this.editingId();
      if (id) {
        await firstValueFrom(this.profilesApi.update(id, payload));
      } else {
        await firstValueFrom(this.profilesApi.create(payload));
      }
      this.resetForm();
      await this.reload();
    } catch {
      this.snackBar.open('Nie udało się zapisać profilu. Nazwa musi być unikalna.', 'OK');
    }
  }

  async remove(profile: SourceProfile): Promise<void> {
    if (!confirm(`Usunąć profil „${profile.name}”? Pliki go używające zostaną odpięte.`)) {
      return;
    }
    await firstValueFrom(this.profilesApi.delete(profile.id));
    await this.reload();
  }

  private async reload(): Promise<void> {
    this.profiles.set(await firstValueFrom(this.profilesApi.list()));
  }
}
