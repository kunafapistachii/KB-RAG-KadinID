import { type ClassValue, clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDate(date: Date | string): string {
  return new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  }).format(new Date(date));
}

export function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

// "45", "45A", "10a" -> [45, "A"] — legal citation numbers carry an optional
// trailing letter suffix (e.g. Pasal 45A), so plain numeric or string sort
// gets both the number and the suffix wrong.
function splitNumericSuffix(value: string | null): [number, string] {
  if (!value) return [Number.POSITIVE_INFINITY, ''];
  const match = value.match(/^(\d+)([A-Za-z]*)$/);
  if (!match) return [Number.POSITIVE_INFINITY, value];
  return [Number(match[1]), match[2].toUpperCase()];
}

/** Ascending by pasal number, then ayat number, both suffix-aware. Items
 * with no pasal_number sort last. */
export function comparePasalAyat(
  a: { pasal_number: string | null; ayat_number: string | null },
  b: { pasal_number: string | null; ayat_number: string | null }
): number {
  const [aPasalNum, aPasalSuffix] = splitNumericSuffix(a.pasal_number);
  const [bPasalNum, bPasalSuffix] = splitNumericSuffix(b.pasal_number);
  if (aPasalNum !== bPasalNum) return aPasalNum - bPasalNum;
  if (aPasalSuffix !== bPasalSuffix) return aPasalSuffix.localeCompare(bPasalSuffix);

  const [aAyatNum, aAyatSuffix] = splitNumericSuffix(a.ayat_number);
  const [bAyatNum, bAyatSuffix] = splitNumericSuffix(b.ayat_number);
  if (aAyatNum !== bAyatNum) return aAyatNum - bAyatNum;
  return aAyatSuffix.localeCompare(bAyatSuffix);
}
