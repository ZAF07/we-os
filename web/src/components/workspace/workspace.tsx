"use client";

import { useCallback, useEffect, useState, useTransition } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { StatusPill } from "@/components/ui/status-pill";
import { StepTab } from "@/components/ui/step-tab";
import {
  approveStageAction,
  loadStage,
  loadVersion,
  reopenStageAction,
  reviseStageAction,
  startRunAction,
  type StageView,
} from "@/app/campaigns/[slug]/actions";
import type { Campaign, CampaignStage } from "@/lib/engine";
import { statusLabel } from "@/lib/campaigns";
import { statusDotClass } from "@/lib/status";
import {
  defaultStageKey,
  stageStatus,
  stageTitle,
  toPhases,
} from "@/lib/workspace";
import { cn } from "@/lib/utils";

import {
  DeliverableContent,
  StaleBanner,
  VersionHistory,
} from "./deliverable-view";
import { ApprovalGate, ApprovedPanel } from "./decision-panel";
import { RunProgress } from "./run-progress";
import { useRunEvents } from "./use-run-events";

/**
 * Renders the Workspace: where the business owner reads what the system
 * produced and decides.
 *
 * Everything shown comes from the engine. The stepper renders operator Phases
 * driven by the Phase each stage reports, and the campaign's lifecycle status
 * renders separately — two axes, not one (ADR-0017).
 *
 * Args:
 *   campaign: The campaign as the engine reports it.
 *   runId: The run currently working on it, or null when none is in flight.
 */
export function Workspace({
  campaign,
  runId,
}: {
  campaign: Campaign;
  runId: string | null;
}) {
  const router = useRouter();
  const phases = toPhases(campaign.stages);
  const [selectedKey, setSelectedKey] = useState(
    () => defaultStageKey(campaign.stages) ?? "",
  );
  const [loaded, setLoaded] = useState<{ key: string; view: StageView } | null>(
    null,
  );
  const [shown, setShown] = useState<{
    key: string;
    version: number;
    content: string | null;
  } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, startAction] = useTransition();

  const selected =
    campaign.stages.find((stage) => stage.key === selectedKey) ??
    campaign.stages[0];
  const { events, finished } = useRunEvents(runId);

  const view = loaded?.key === selectedKey ? loaded.view : null;
  const shownVersion = shown?.key === selectedKey ? shown.version : null;
  const shownContent = shown?.key === selectedKey ? shown.content : null;

  useEffect(() => {
    let current = true;
    loadStage(campaign.id, selectedKey)
      .then((stageView) => {
        if (current) setLoaded({ key: selectedKey, view: stageView });
      })
      .catch(() => {
        if (current) setError("Could not load this stage. Try again.");
      });
    return () => {
      current = false;
    };
  }, [campaign.id, selectedKey]);

  useEffect(() => {
    if (finished) router.refresh();
  }, [finished, router]);

  const run = useCallback(
    (action: () => Promise<{ error: string | null }>) => {
      setError(null);
      startAction(async () => {
        const result = await action();
        if (result.error) setError(result.error);
        else router.refresh();
      });
    },
    [router],
  );

  const showVersion = (version: number) => {
    const key = selectedKey;
    setShown({ key, version, content: null });
    loadVersion(campaign.id, key, version).then((detail) => {
      setShown({ key, version, content: detail?.content ?? null });
    });
  };

  return (
    <main className="flex min-w-0 flex-1 flex-col overflow-hidden">
      <div className="border-b bg-card px-4 pt-3.5 md:px-6">
        <div className="flex flex-wrap items-center gap-2 text-[12.5px] text-muted-foreground">
          <Link
            href="/campaigns"
            className="text-muted-foreground no-underline hover:text-primary"
          >
            Campaigns
          </Link>
          <span>/</span>
          <span className="font-semibold text-foreground">{campaign.name}</span>
          <StatusPill status={statusLabel(campaign.status)} />
        </div>
        <div className="scrollbar-none mt-3 flex gap-1 overflow-x-auto">
          {phases.map((phase, index) => (
            <StepTab
              key={phase.name}
              mark={String(index + 1)}
              label={phase.name}
              done={phase.status === "Approved"}
              active={phase.stages.some((stage) => stage.key === selectedKey)}
              onClick={() => setSelectedKey(phase.stages[0].key)}
            />
          ))}
        </div>
      </div>

      <div className="flex min-h-0 flex-1 flex-col overflow-auto lg:flex-row">
        <StageNav
          stages={campaign.stages}
          selectedKey={selectedKey}
          onSelect={setSelectedKey}
        />

        <div className="flex-1 overflow-visible px-4 py-6 lg:min-w-[420px] lg:overflow-auto lg:px-7">
          <StageDocument
            stage={selected}
            view={view}
            shownVersion={shownVersion}
            shownContent={shownContent}
            pending={pending}
            onRerun={() => run(() => startRunAction(campaign.id))}
            onShowVersion={showVersion}
          />
        </div>

        <div className="w-full shrink-0 space-y-3 border-t bg-card p-4 lg:w-[312px] lg:overflow-auto lg:border-t-0 lg:border-l">
          {error && (
            <p
              role="alert"
              className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-[12.5px] text-red-800"
            >
              {error}
            </p>
          )}

          {runId && <RunProgress events={events} finished={finished} />}

          <DecisionRail
            campaign={campaign}
            stage={selected}
            runId={runId}
            pending={pending}
            onApprove={(stageKey) =>
              run(() => approveStageAction(campaign.id, runId!, stageKey))
            }
            onRevise={(stageKey, feedback) =>
              run(() =>
                reviseStageAction(campaign.id, runId!, stageKey, feedback),
              )
            }
            onReopen={(stageKey, feedback) =>
              run(() => reopenStageAction(campaign.id, stageKey, feedback))
            }
            onStart={() => run(() => startRunAction(campaign.id))}
          />
        </div>
      </div>
    </main>
  );
}

/**
 * Renders the left-hand stage list, one entry per engine stage.
 *
 * The stepper groups stages into Phases; this list is where the individual
 * stages under a Phase are reachable, named as the interface names them.
 *
 * Args:
 *   stages: The campaign's stages in pipeline order.
 *   selectedKey: The stage currently shown.
 *   onSelect: Shows a stage.
 */
function StageNav({
  stages,
  selectedKey,
  onSelect,
}: {
  stages: CampaignStage[];
  selectedKey: string;
  onSelect: (key: string) => void;
}) {
  return (
    <nav
      aria-label="Stages"
      className="hidden w-[212px] shrink-0 overflow-y-auto border-r bg-card px-2.5 py-3 lg:block"
    >
      <div className="px-2 pb-2 text-[10.5px] font-bold tracking-wider text-slate-400 uppercase">
        Stages
      </div>
      {stages.map((stage) => {
        const active = stage.key === selectedKey;
        const status = stageStatus(stage.state);
        return (
          <button
            key={stage.key}
            onClick={() => onSelect(stage.key)}
            className={cn(
              "flex w-full cursor-pointer gap-[9px] rounded-lg p-2 text-left",
              active ? "bg-indigo-50" : "hover:bg-slate-100",
            )}
          >
            <span
              className={cn(
                "mt-[5px] size-[7px] shrink-0 rounded-full",
                statusDotClass(status),
              )}
            />
            <span>
              <span
                className={cn(
                  "block text-[13px]",
                  active ? "font-bold text-primary" : "font-medium",
                )}
              >
                {stageTitle(stage.key)}
              </span>
              <span className="block text-[11px] text-slate-400">{status}</span>
            </span>
          </button>
        );
      })}
    </nav>
  );
}

/**
 * Renders the selected stage: its deliverable, or an honest empty state.
 *
 * Args:
 *   stage: The selected stage.
 *   view: Its deliverable and versions, or null while loading.
 *   shownVersion: The historical version being shown, if any.
 *   shownContent: That version's content, or null while loading.
 *   pending: Whether an action is in flight.
 *   onRerun: Starts a run to clear staleness.
 *   onShowVersion: Shows a historical version.
 */
function StageDocument({
  stage,
  view,
  shownVersion,
  shownContent,
  pending,
  onRerun,
  onShowVersion,
}: {
  stage: CampaignStage;
  view: StageView | null;
  shownVersion: number | null;
  shownContent: string | null;
  pending: boolean;
  onRerun: () => void;
  onShowVersion: (version: number) => void;
}) {
  const title = stageTitle(stage.key);

  if (view === null) {
    return (
      <div className="max-w-[720px]">
        <h2 className="text-xl font-bold tracking-tight">{title}</h2>
        <p className="mt-2 text-[13px] text-muted-foreground">Loading…</p>
      </div>
    );
  }

  return (
    <div className="max-w-[720px]">
      {stage.stale && <StaleBanner onRerun={onRerun} pending={pending} />}
      <div className="flex items-center gap-2">
        <StatusPill status={stageStatus(stage.state)} />
        {stage.latest_version !== null && (
          <span className="text-[12px] text-muted-foreground">
            {shownVersion !== null && shownVersion !== stage.latest_version
              ? `Showing v${shownVersion} of ${stage.latest_version}`
              : `v${stage.latest_version}`}
          </span>
        )}
      </div>
      <h2 className="mt-2.5 mb-[18px] text-xl font-bold tracking-tight">
        {title}
      </h2>

      {view.deliverable === null ? (
        <p className="rounded-xl border border-dashed border-slate-300 bg-slate-50 px-[18px] py-4 text-[13px] text-muted-foreground">
          Nothing produced yet. This stage runs once everything before it is
          approved.
        </p>
      ) : shownVersion !== null && shownVersion !== stage.latest_version ? (
        shownContent === null ? (
          <p className="text-[13px] text-muted-foreground">Loading version…</p>
        ) : (
          <DeliverableContent content={shownContent} />
        )
      ) : (
        <DeliverableContent content={view.deliverable.content} />
      )}

      <VersionHistory
        versions={view.versions}
        selected={shownVersion}
        onSelect={onShowVersion}
      />
    </div>
  );
}

/**
 * Renders the decision the campaign is asking for, if it is asking for one.
 *
 * Args:
 *   campaign: The campaign, for its lifecycle status.
 *   stage: The selected stage.
 *   runId: The live run, or null when none is in flight.
 *   pending: Whether an action is in flight.
 *   onApprove: Approves the waiting stage.
 *   onRevise: Sends the waiting stage back with feedback.
 *   onReopen: Re-opens an approved stage.
 *   onStart: Starts a run.
 */
function DecisionRail({
  campaign,
  stage,
  runId,
  pending,
  onApprove,
  onRevise,
  onReopen,
  onStart,
}: {
  campaign: Campaign;
  stage: CampaignStage;
  runId: string | null;
  pending: boolean;
  onApprove: (stageKey: string) => void;
  onRevise: (stageKey: string, feedback: string) => void;
  onReopen: (stageKey: string, feedback: string) => void;
  onStart: () => void;
}) {
  if (stage.state === "awaiting_approval" && runId !== null) {
    return (
      <ApprovalGate
        stageName={stageTitle(stage.key)}
        onApprove={() => onApprove(stage.key)}
        onRevise={(feedback) => onRevise(stage.key, feedback)}
        pending={pending}
      />
    );
  }

  if (stage.state === "completed") {
    return (
      <ApprovedPanel
        stageName={stageTitle(stage.key)}
        onReopen={(feedback) => onReopen(stage.key, feedback)}
        pending={pending}
      />
    );
  }

  if (runId === null && campaign.status !== "archived") {
    return (
      <div className="rounded-xl border bg-card px-4 py-3.5">
        <div className="text-[11px] font-bold tracking-wide text-muted-foreground uppercase">
          Nothing running
        </div>
        <p className="mt-1 text-[12.5px] text-muted-foreground">
          Start a run to work through the pipeline. You will be asked to approve
          each stage before the next one begins.
        </p>
        <button
          onClick={onStart}
          disabled={pending}
          className="mt-3 w-full cursor-pointer rounded-lg bg-primary py-2 text-[13px] font-semibold text-primary-foreground hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {pending ? "Starting…" : "Start run"}
        </button>
      </div>
    );
  }

  return null;
}
