import { Pipe, PipeTransform } from '@angular/core';

@Pipe({ name: 'pln' })
export class PlnPipe implements PipeTransform {
  private readonly formatter = new Intl.NumberFormat('pl-PL', {
    style: 'currency',
    currency: 'PLN',
  });

  transform(value: string | number | null | undefined): string {
    if (value === null || value === undefined || value === '') {
      return '—';
    }
    return this.formatter.format(Number(value));
  }
}
