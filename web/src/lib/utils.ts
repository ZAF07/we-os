import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

/**
 * Merges class names, resolving Tailwind utility conflicts.
 *
 * Args:
 *   inputs: Class values (strings, arrays, conditionals) to merge.
 *
 * Returns:
 *   A single merged class string.
 */
export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}
