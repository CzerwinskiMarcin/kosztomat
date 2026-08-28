import { ChangeDetectionStrategy, Component, output } from '@angular/core';

@Component({
  selector: 'app-dropzone',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <label
      class="dropzone"
      [class.dropzone--active]="isDragging"
      (dragover)="onDragOver($event)"
      (dragleave)="onDragLeave($event)"
      (drop)="onDrop($event)"
    >
      <input
        type="file"
        accept=".csv,.txt,text/csv,text/plain"
        (change)="onInput($event)"
      />
      <strong>Upuść plik CSV</strong>
      <span>albo kliknij, żeby wybrać eksport z banku albo budżetu (.csv, .txt)</span>
    </label>
  `,
  styles: `
    .dropzone {
      display: flex;
      flex-direction: column;
      gap: 0.35rem;
      align-items: center;
      justify-content: center;
      min-height: 160px;
      padding: 1.5rem;
      border: 1px dashed var(--kz-accent-dim);
      border-radius: 16px;
      background: color-mix(in srgb, var(--kz-accent) 8%, var(--kz-surface));
      cursor: pointer;
      text-align: center;
      transition: border-color 0.15s ease, background 0.15s ease;
    }
    .dropzone--active,
    .dropzone:hover {
      border-color: var(--kz-accent);
      background: color-mix(in srgb, var(--kz-accent) 14%, var(--kz-surface));
    }
    input {
      display: none;
    }
    span {
      color: var(--kz-muted);
      font-size: 0.95rem;
    }
  `,
})
export class DropzoneComponent {
  readonly fileSelected = output<File>();
  isDragging = false;

  onDragOver(event: DragEvent): void {
    event.preventDefault();
    this.isDragging = true;
  }

  onDragLeave(event: DragEvent): void {
    event.preventDefault();
    this.isDragging = false;
  }

  onDrop(event: DragEvent): void {
    event.preventDefault();
    this.isDragging = false;
    const file = event.dataTransfer?.files[0];
    if (file) {
      this.fileSelected.emit(file);
    }
  }

  onInput(event: Event): void {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    if (file) {
      this.fileSelected.emit(file);
      input.value = '';
    }
  }
}
