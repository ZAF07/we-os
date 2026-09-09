"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth, useOrganizationList } from "@clerk/nextjs";

import {
  recordTier,
  type RecordTierResult,
} from "@/app/(welcome)/welcome/actions";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { tierParam, type Tier } from "@/lib/tiers";

/**
 * Brings a business into being: a name, then the Organization, then the tier.
 *
 * The order is forced and kept (ADR-0027). The Organization must exist before
 * the session can carry an organization claim, and the session must carry that
 * claim before the engine can mint the tenant the tier attaches to. Activating
 * the Organization mutates the browser's session, which is why the whole
 * sequence runs here on the client: create, activate, refresh the session
 * token so the next request carries the claim, then record the tier through a
 * server action, then Home.
 *
 * A failure at the tier call leaves the person here with the message and a
 * retry. The Organization already exists by then, so the retry is the tier
 * call alone — which the engine accepts repeatedly — and one attempt leaves
 * one business.
 *
 * When the session already carries a business there is nothing to name, so
 * the tier is recorded on arrival and the person continues to Home. That is
 * how a business whose tier was never recorded — sent by Home to choose one —
 * finishes. A business that already has a different tier is refused by the
 * engine, and no retry can change that, so that refusal is shown without one.
 *
 * Args:
 *   tier: The tier the person chose.
 *   businessExists: Whether the session already carries an Organization.
 */
export function WelcomeForm({
  tier,
  businessExists,
}: {
  tier: Tier;
  businessExists: boolean;
}) {
  const router = useRouter();
  const { getToken } = useAuth();
  const { createOrganization, setActive } = useOrganizationList();
  const [name, setName] = useState("");
  const [created, setCreated] = useState(businessExists);
  const [busy, setBusy] = useState(businessExists);
  const [error, setError] = useState<string | null>(null);
  const [retryable, setRetryable] = useState(true);
  const tierName = tierParam(tier);

  const afterRecordTier = useCallback(
    (result: RecordTierResult) => {
      if (result.error !== null) {
        setError(result.error);
        setRetryable(result.retryable);
        setBusy(false);
        return;
      }
      router.replace("/home");
    },
    [router],
  );

  const finish = useCallback(
    async () => afterRecordTier(await recordTier(tierName)),
    [afterRecordTier, tierName],
  );

  useEffect(() => {
    if (!businessExists) return;
    let superseded = false;
    void recordTier(tierName).then((result) => {
      if (!superseded) afterRecordTier(result);
    });
    return () => {
      superseded = true;
    };
  }, [businessExists, afterRecordTier, tierName]);

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy || !createOrganization || !setActive) return;
    setBusy(true);
    setError(null);
    try {
      const organization = await createOrganization({ name: name.trim() });
      await setActive({ organization: organization.id });
      await getToken({ skipCache: true });
      setCreated(true);
    } catch (failure) {
      setError(
        failure instanceof Error
          ? failure.message
          : "Could not create the business. Try again.",
      );
      setBusy(false);
      return;
    }
    await finish();
  }

  function retry() {
    setBusy(true);
    setError(null);
    void finish();
  }

  return (
    <section
      aria-labelledby="welcome-heading"
      className="w-full max-w-md rounded-[20px] border bg-card p-8 shadow-[0_20px_50px_-24px_rgba(15,23,42,0.25)]"
    >
      <p className="text-[13px] font-semibold tracking-[0.08em] text-primary uppercase">
        Welcome
      </p>
      {created ? (
        <>
          <h1
            id="welcome-heading"
            className="mt-3 text-2xl font-bold tracking-tight"
          >
            {error === null
              ? "One moment."
              : retryable
                ? "Almost there."
                : "Your business already has a tier."}
          </h1>
          <p className="mt-2 text-[15px] leading-relaxed text-slate-600">
            {error === null
              ? `Recording the ${tier.name} tier for your business.`
              : retryable
                ? "Your business exists, but its tier was not recorded."
                : "A tier is chosen once, so there is nothing to record here."}
          </p>
          {error !== null && (
            <p role="alert" className="mt-4 text-sm text-destructive">
              {error}
            </p>
          )}
          {error !== null && (
            <div className="mt-6 flex flex-wrap gap-3">
              {retryable && (
                <Button size="xl" onClick={retry} disabled={busy}>
                  Try again
                </Button>
              )}
              <Button
                asChild
                size="xl"
                variant={retryable ? "outline" : "default"}
              >
                <Link href="/home">Go to Home</Link>
              </Button>
            </div>
          )}
        </>
      ) : (
        <>
          <h1
            id="welcome-heading"
            className="mt-3 text-2xl font-bold tracking-tight"
          >
            Name your business.
          </h1>
          <p className="mt-2 text-[15px] leading-relaxed text-slate-600">
            You chose the {tier.name} tier. Its marketing lives here from now
            on.
          </p>
          <form onSubmit={submit} className="mt-6 flex flex-col gap-4">
            <div className="flex flex-col gap-2">
              <Label htmlFor="business-name">Business name</Label>
              <Input
                id="business-name"
                value={name}
                onChange={(event) => setName(event.target.value)}
                placeholder="Coast Coffee"
                autoComplete="organization"
                autoFocus
                required
                disabled={busy}
              />
            </div>
            {error && (
              <p role="alert" className="text-sm text-destructive">
                {error}
              </p>
            )}
            <Button
              type="submit"
              size="xl"
              disabled={busy || !createOrganization || name.trim() === ""}
            >
              {busy ? "Setting up…" : "Create my business"}
            </Button>
          </form>
        </>
      )}
    </section>
  );
}
