"use client";

import { Label } from "@/components/ui/label";
import { StepTab } from "@/components/ui/step-tab";

/**
 * Renders the numbered step-progress row shared by the wizards.
 *
 * Args:
 *   steps: Ordered step names.
 *   current: Index of the active step.
 *
 * Returns:
 *   The progress indicator element.
 */
export function WizardProgress({
  steps,
  current,
}: {
  steps: string[];
  current: number;
}) {
  return (
    <div className="scrollbar-none flex gap-1 overflow-x-auto">
      {steps.map((name, index) => (
        <StepTab
          key={name}
          mark={String(index + 1)}
          label={name}
          done={index < current}
          active={index === current}
        />
      ))}
    </div>
  );
}

/**
 * Renders the wizard page frame: heading, note, progress, body card,
 * and Back/Next footer.
 *
 * Args:
 *   title: Page heading.
 *   subtitle: Line under the heading.
 *   note: Optional expectation-setting callout (e.g. manual entry).
 *   steps: Ordered step names.
 *   current: Index of the active step.
 *   error: Optional validation message shown above the footer.
 *   nextLabel: Label for the primary action on the final step.
 *   onBack: Called when Back is clicked (hidden on the first step).
 *   onNext: Called when Next / the final action is clicked.
 *   children: The active step's fields.
 *
 * Returns:
 *   The wizard layout element.
 */
export function WizardShell({
  title,
  subtitle,
  note,
  steps,
  current,
  error,
  nextLabel,
  onBack,
  onNext,
  children,
}: {
  title: string;
  subtitle: string;
  note?: string;
  steps: string[];
  current: number;
  error?: string;
  nextLabel: string;
  onBack: () => void;
  onNext: () => void;
  children: React.ReactNode;
}) {
  const isLast = current === steps.length - 1;
  return (
    <main className="flex-1 overflow-y-auto px-4 py-6 md:px-8 md:py-7">
      <div className="max-w-[720px]">
        <div className="text-xs font-semibold tracking-wider text-muted-foreground uppercase">
          Step {current + 1} of {steps.length}
        </div>
        <h1 className="mt-1 text-[22px] font-bold tracking-tight">{title}</h1>
        <p className="mt-1 text-[13px] text-muted-foreground">{subtitle}</p>
        {note && (
          <div className="mt-3 rounded-[10px] border border-indigo-200 bg-indigo-50 px-3.5 py-2.5 text-[12.5px] text-indigo-900">
            {note}
          </div>
        )}
        <div className="mt-4 border-b">
          <WizardProgress steps={steps} current={current} />
        </div>
        <div className="mt-5 flex flex-col gap-4 rounded-xl border bg-card px-[22px] py-5">
          {children}
        </div>
        {error && (
          <div className="mt-3 rounded-[10px] border border-red-200 bg-red-50 px-3.5 py-2.5 text-[12.5px] text-red-700">
            {error}
          </div>
        )}
        <div className="mt-4 flex items-center justify-between">
          {current > 0 ? (
            <button
              onClick={onBack}
              className="cursor-pointer rounded-lg border bg-card px-3.5 py-2 text-[13px] font-semibold hover:bg-slate-50"
            >
              ← Back
            </button>
          ) : (
            <span />
          )}
          <button
            onClick={onNext}
            className="cursor-pointer rounded-lg bg-primary px-3.5 py-2 text-[13px] font-semibold text-primary-foreground hover:bg-indigo-700"
          >
            {isLast ? nextLabel : "Next →"}
          </button>
        </div>
      </div>
    </main>
  );
}

/**
 * Renders a labeled form field with required-marker and error line.
 *
 * Args:
 *   label: Field label.
 *   htmlFor: Id of the wrapped control.
 *   required: Whether the field is required.
 *   error: Whether to show the required-field error line.
 *   hint: Optional format hint under the label.
 *   children: The input or textarea control.
 *
 * Returns:
 *   The field element.
 */
export function Field({
  label,
  htmlFor,
  required,
  error,
  hint,
  children,
}: {
  label: string;
  htmlFor: string;
  required?: boolean;
  error?: boolean;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <Label htmlFor={htmlFor} className="text-[13px] font-semibold">
        {label}
        {required && <span className="text-destructive">*</span>}
      </Label>
      {hint && (
        <div className="-mt-1 text-xs text-muted-foreground">{hint}</div>
      )}
      {children}
      {error && (
        <div className="text-xs font-semibold text-destructive">
          This field is required.
        </div>
      )}
    </div>
  );
}
