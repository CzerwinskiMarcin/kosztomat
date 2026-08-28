import { ChangeDetectionStrategy, Component, input } from '@angular/core';

@Component({
  selector: 'app-empty-state',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <section class="empty" role="status">
      <h3>{{ title() }}</h3>
      <p>{{ message() }}</p>
      <ng-content />
    </section>
  `,
  styles: `
    .empty {
      padding: 2.5rem 1.5rem;
      text-align: center;
      color: var(--kz-muted);
      border: 1px dashed var(--kz-border);
      border-radius: 16px;
      background: color-mix(in srgb, var(--kz-surface) 70%, transparent);
    }
    h3 {
      margin: 0 0 0.5rem;
      color: var(--kz-text);
      font-size: 1.1rem;
    }
    p {
      margin: 0 0 1rem;
      max-width: 36rem;
      margin-inline: auto;
    }
  `,
})
export class EmptyStateComponent {
  readonly title = input.required<string>();
  readonly message = input.required<string>();
}
