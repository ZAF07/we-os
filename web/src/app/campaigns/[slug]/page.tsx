"use client";

import Link from "next/link";
import { useParams } from "next/navigation";

import { StatusPill } from "@/components/ui/status-pill";
import { StepTab } from "@/components/ui/step-tab";
import type { CreatedCampaign } from "@/lib/campaigns";
import {
  AI_ACTIONS,
  AI_NOTES,
  campaignRows,
  EVIDENCE,
  SCORECARD,
  STAGE_NAMES,
  stageDetail,
  stageStatus,
  stageSubtitles,
  STRATEGY_STAGE_INDEX,
} from "@/lib/mock-data";
import { statusDotClass, statusPillClasses, type Status } from "@/lib/status";
import { useDemoStore } from "@/lib/store";
import { cn } from "@/lib/utils";

/**
 * Returns a created (wizard-built) campaign's stage status.
 *
 * Args:
 *   stage: Stage index 0–7.
 *
 * Returns:
 *   Draft for the Brief stage, Not started for everything after.
 */
function createdStageStatus(stage: number): Status {
  return stage === 0 ? "Draft" : "Not started";
}

const CREATED_SUBTITLES = [
  "Drafted just now",
  "Starts after Brief",
  "Not started",
  "Not started",
  "Not started",
  "Not started",
  "Not started",
  "Not started",
];

/** Renders an inline evidence-source reference chip (e.g. S1). */
function SourceChip({ id }: { id: string }) {
  return (
    <a
      href="#"
      className="rounded-[5px] bg-indigo-50 px-1.5 py-px text-[11px] font-semibold no-underline"
    >
      {id}
    </a>
  );
}

/**
 * Renders the horizontal 8-stage stepper.
 *
 * Args:
 *   statusFor: Maps a stage index to its canonical status.
 */
function Stepper({ statusFor }: { statusFor: (stage: number) => Status }) {
  const stage = useDemoStore((state) => state.stage);
  const setStage = useDemoStore((state) => state.setStage);

  return (
    <div className="scrollbar-none mt-3 flex gap-1 overflow-x-auto">
      {STAGE_NAMES.map((name, index) => (
        <StepTab
          key={name}
          mark={String(index + 1)}
          label={name}
          done={statusFor(index) === "Approved"}
          active={stage === index}
          onClick={() => setStage(index)}
        />
      ))}
    </div>
  );
}

/**
 * Renders the left-hand stage list with status dots and subtitles.
 *
 * Args:
 *   statusFor: Maps a stage index to its canonical status.
 *   subtitles: Per-stage subtitle lines.
 */
function StageNav({
  statusFor,
  subtitles,
}: {
  statusFor: (stage: number) => Status;
  subtitles: string[];
}) {
  const stage = useDemoStore((state) => state.stage);
  const setStage = useDemoStore((state) => state.setStage);

  return (
    <nav
      aria-label="Stages"
      className="hidden w-[212px] shrink-0 overflow-y-auto border-r bg-card px-2.5 py-3 lg:block"
    >
      <div className="px-2 pb-2 text-[10.5px] font-bold tracking-wider text-slate-400 uppercase">
        Stages
      </div>
      {STAGE_NAMES.map((name, index) => {
        const active = stage === index;
        return (
          <button
            key={name}
            onClick={() => setStage(index)}
            className={cn(
              "flex w-full cursor-pointer gap-[9px] rounded-lg p-2 text-left",
              active ? "bg-indigo-50" : "hover:bg-slate-100",
            )}
          >
            <span
              className={cn(
                "mt-[5px] size-[7px] shrink-0 rounded-full",
                statusDotClass(statusFor(index)),
              )}
            />
            <span>
              <span
                className={cn(
                  "block text-[13px]",
                  active ? "font-bold text-primary" : "font-medium",
                )}
              >
                {name}
              </span>
              <span className="block text-[11px] text-slate-400">
                {subtitles[index]}
              </span>
            </span>
          </button>
        );
      })}
    </nav>
  );
}

/** Renders the Fernway Strategy-stage document (the demo's hero content). */
function StrategyDocument() {
  return (
    <div className="max-w-[660px]">
      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        <span
          className={cn(
            "rounded-md px-2 py-0.5 text-[11px] font-semibold",
            statusPillClasses("Ready for review"),
          )}
        >
          v2 · Ready for review
        </span>
        <span>Drafted from the research readout · 14 sources</span>
      </div>
      <h2 className="mt-2.5 mb-1 text-xl font-bold tracking-tight">
        Audience &amp; positioning strategy
      </h2>
      <p className="mb-[18px] text-[13px] text-muted-foreground">
        Defines who we speak to and the single idea every asset in this campaign
        supports.
      </p>
      <div className="flex flex-col gap-[18px] rounded-xl border bg-card px-[22px] py-5">
        <div>
          <div className="mb-1.5 text-[11px] font-bold tracking-wide text-muted-foreground uppercase">
            Primary audience
          </div>
          <p className="text-sm">
            Low-waste households, 28–45, urban and suburban, already buying eco
            cleaning products but frustrated by cost and shipping waste. They
            respond to practical economics over moral framing.{" "}
            <SourceChip id="S1" /> <SourceChip id="S3" />
          </p>
        </div>
        <div className="border-t border-slate-100 pt-4">
          <div className="mb-1.5 text-[11px] font-bold tracking-wide text-muted-foreground uppercase">
            Positioning statement
          </div>
          <blockquote className="rounded-r-lg border-l-[3px] border-primary bg-slate-50 px-4 py-3 text-[15px] font-medium">
            Fernway is the refill system that pays for itself — premium home
            care that costs less every month you keep it.
          </blockquote>
        </div>
        <div className="border-t border-slate-100 pt-4">
          <div className="mb-1.5 text-[11px] font-bold tracking-wide text-muted-foreground uppercase">
            Message pillars
          </div>
          <div className="flex flex-col gap-2 text-sm">
            <div>
              <strong>1. Refill economics</strong> — cost-per-clean vs.
              single-use, shown with real numbers. <SourceChip id="S2" />
            </div>
            <div>
              <strong>2. Designed to stay</strong> — the bottle as a permanent
              object, not packaging.
            </div>
            <div>
              <strong>3. No compromise</strong> — third-party efficacy results
              against the two leading brands. <SourceChip id="S4" />
            </div>
          </div>
        </div>
        <div className="border-t border-slate-100 pt-4">
          <div className="mb-1.5 text-[11px] font-bold tracking-wide text-muted-foreground uppercase">
            Ruled out
          </div>
          <p className="text-[13.5px] text-slate-700">
            A sustainability-first angle: it tested 2.4× weaker on purchase
            intent with this segment and overlaps with three competitors&apos;
            current messaging.
          </p>
        </div>
      </div>
    </div>
  );
}

/** Renders a non-Strategy stage's done / inputs / after detail. */
function GenericStageDocument() {
  const stage = useDemoStore((state) => state.stage);
  const approved = useDemoStore((state) => state.approved);
  const reopened = useDemoStore((state) => state.reopened);
  const staleCleared = useDemoStore((state) => state.staleCleared);
  const detail = stageDetail(stage, approved);
  const status = stageStatus(stage, approved, reopened, staleCleared);

  return (
    <div className="max-w-[660px]">
      {status === "Stale" && <StaleBanner />}
      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        <StatusPill status={status} />
      </div>
      <h2 className="mt-2.5 mb-1 text-xl font-bold tracking-tight">
        {detail.title}
      </h2>
      <p className="mb-[18px] text-[13px] text-muted-foreground">
        {detail.desc}
      </p>
      <div className="grid grid-cols-1 gap-3.5 sm:grid-cols-2">
        <div className="rounded-xl border bg-card px-[18px] py-4">
          <div className="mb-2 text-[11px] font-bold tracking-wide text-muted-foreground uppercase">
            Work completed
          </div>
          <div className="flex flex-col gap-[7px] text-[13px]">
            {detail.done.map((item) => (
              <div key={item} className="flex gap-[7px]">
                <span className="text-emerald-500">✓</span>
                <span>{item}</span>
              </div>
            ))}
          </div>
        </div>
        <div className="rounded-xl border bg-card px-[18px] py-4">
          <div className="mb-2 text-[11px] font-bold tracking-wide text-muted-foreground uppercase">
            Inputs needed from you
          </div>
          <div className="flex flex-col gap-[7px] text-[13px]">
            {detail.inputs.map((item) => (
              <div key={item} className="flex gap-[7px]">
                <span className="text-amber-500">○</span>
                <span>{item}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
      <div className="mt-3.5 rounded-xl border border-dashed border-slate-300 bg-slate-50 px-[18px] py-3.5 text-[13px] text-muted-foreground">
        <strong className="text-slate-700">After this stage:</strong>{" "}
        {detail.after}
      </div>
    </div>
  );
}

/**
 * Renders the Brief stage of a wizard-created campaign from its
 * entered inputs.
 *
 * Args:
 *   campaign: The campaign created through the new-campaign wizard.
 */
function CreatedBriefDocument({ campaign }: { campaign: CreatedCampaign }) {
  const fields = [
    { k: "Primary objective", v: campaign.objective },
    { k: "Success metric", v: campaign.metric },
    { k: "Desired customer action", v: campaign.action },
    {
      k: "Primary audience",
      v: campaign.funnel
        ? `${campaign.audience} · ${campaign.funnel}`
        : campaign.audience,
    },
    { k: "Offer", v: campaign.offer },
    { k: "Call to action", v: campaign.cta },
    { k: "Budget", v: campaign.budget },
    { k: "Timeline", v: `${campaign.start} → ${campaign.end}` },
    { k: "Channels", v: campaign.channels.join(", ") },
    { k: "Owner & approver", v: campaign.owner },
  ];

  return (
    <div className="max-w-[660px]">
      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        <StatusPill status="Draft" />
        <span>Drafted from your campaign request · just now</span>
      </div>
      <h2 className="mt-2.5 mb-1 text-xl font-bold tracking-tight">
        Campaign brief
      </h2>
      <p className="mb-[18px] text-[13px] text-muted-foreground">
        The goal, budget and constraints this campaign was created from.
      </p>
      <div className="flex flex-col gap-[18px] rounded-xl border bg-card px-[22px] py-5">
        <div>
          <div className="mb-1.5 text-[11px] font-bold tracking-wide text-muted-foreground uppercase">
            Why this campaign
          </div>
          <p className="text-sm">{campaign.reason}</p>
        </div>
        <div className="border-t border-slate-100 pt-4">
          <div className="mb-1.5 text-[11px] font-bold tracking-wide text-muted-foreground uppercase">
            Brief
          </div>
          <div className="flex flex-col">
            {fields.map((field) => (
              <div
                key={field.k}
                className="flex justify-between gap-2.5 border-b border-slate-100 py-[7px] text-[13px] last:border-b-0"
              >
                <span className="text-muted-foreground">{field.k}</span>
                <span className="text-right font-semibold">{field.v}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
      <div className="mt-3.5 rounded-xl border border-dashed border-slate-300 bg-slate-50 px-[18px] py-3.5 text-[13px] text-muted-foreground">
        <strong className="text-slate-700">After this stage:</strong> Research
        runs against this brief before any strategy is proposed.
      </div>
    </div>
  );
}

/** Renders the Strategy-stage decision panel (Approve / Request changes). */
function DecisionPanel() {
  const approve = useDemoStore((state) => state.approve);
  const setRightTab = useDemoStore((state) => state.setRightTab);

  return (
    <div className="rounded-xl border border-indigo-200 bg-indigo-50 px-4 py-3.5">
      <div className="text-[11px] font-bold tracking-wide text-indigo-700 uppercase">
        Decision required
      </div>
      <div className="mt-1 text-sm font-bold">
        Approve audience &amp; positioning
      </div>
      <div className="mt-2 rounded-lg border border-indigo-200 bg-card px-2.5 py-2 text-xs text-indigo-700">
        <strong>Approval unlocks:</strong> channel strategy draft + content plan
        (est. 14 items). Changing it later re-opens both.
      </div>
      <div className="mt-3 flex gap-2">
        <button
          onClick={approve}
          className="flex-1 cursor-pointer rounded-lg bg-primary py-2 text-[13px] font-semibold text-primary-foreground hover:bg-indigo-700"
        >
          Approve
        </button>
        <button
          onClick={() => setRightTab("comments")}
          className="flex-1 cursor-pointer rounded-lg border border-indigo-200 bg-card py-2 text-[13px] font-semibold hover:bg-slate-50"
        >
          Request changes
        </button>
      </div>
      <div className="mt-2.5 flex gap-3 text-xs font-semibold">
        <a href="#">Edit directly</a>
        <a href="#">Compare versions</a>
        <a href="#">← Prior stage</a>
      </div>
    </div>
  );
}

/** Renders the post-approval confirmation panel with the undo and re-open actions. */
function ApprovedPanel() {
  const undoApprove = useDemoStore((state) => state.undoApprove);
  const reopen = useDemoStore((state) => state.reopen);

  return (
    <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3.5">
      <div className="text-[13.5px] font-bold text-emerald-700">
        ✓ Positioning approved
      </div>
      <div className="mt-1 text-[12.5px] text-emerald-800">
        Plan stage started — channel strategy draft expected today, 4:00 pm.
        You&apos;ll approve it before anything is produced.
      </div>
      <div className="mt-2.5 flex gap-2">
        <button
          onClick={undoApprove}
          className="cursor-pointer rounded-lg border border-emerald-200 bg-card px-2.5 py-[5px] text-xs font-semibold text-emerald-700 hover:bg-emerald-50"
        >
          Return to review
        </button>
        <button
          onClick={reopen}
          className="cursor-pointer rounded-lg border border-orange-200 bg-card px-2.5 py-[5px] text-xs font-semibold text-orange-800 hover:bg-orange-50"
        >
          Re-open this decision
        </button>
      </div>
    </div>
  );
}

/**
 * Renders the panel shown while a re-opened decision is waiting on the owner.
 *
 * Re-opening marks the work downstream Stale rather than regenerating it, so the
 * panel says plainly what has been flagged and that nothing is being redone
 * until the owner asks for it.
 */
function ReopenedPanel() {
  const approve = useDemoStore((state) => state.approve);

  return (
    <div className="rounded-xl border border-orange-200 bg-orange-50 px-4 py-3.5">
      <div className="text-[11px] font-bold tracking-wide text-orange-800 uppercase">
        Re-opened
      </div>
      <div className="mt-1 text-sm font-bold">
        Revise audience &amp; positioning
      </div>
      <div className="mt-2 rounded-lg border border-orange-200 bg-card px-2.5 py-2 text-xs text-orange-800">
        <strong>Plan is now stale.</strong> It was built on the positioning you
        just re-opened. Nothing has been regenerated and nothing has been
        charged — re-run it when you are ready.
      </div>
      <button
        onClick={approve}
        className="mt-3 w-full cursor-pointer rounded-lg bg-primary py-2 text-[13px] font-semibold text-primary-foreground hover:bg-indigo-700"
      >
        Approve revision
      </button>
    </div>
  );
}

/**
 * Renders the banner marking a stage document as resting on a superseded decision.
 *
 * The re-run control lives here rather than elsewhere because staleness is the
 * owner's to resolve: the flag and the one action that clears it belong together,
 * and nothing re-runs until they ask for it.
 */
function StaleBanner() {
  const rerunStale = useDemoStore((state) => state.rerunStale);

  return (
    <div
      role="status"
      className="mb-4 flex flex-wrap items-center gap-x-2 gap-y-2 rounded-xl border border-orange-200 bg-orange-50 px-4 py-3"
    >
      <StatusPill status="Stale" />
      <span className="flex-1 text-[12.5px] text-orange-900">
        Built on a positioning that has since been re-opened. Re-run this stage
        to bring it up to date — it will not update on its own.
      </span>
      <button
        onClick={rerunStale}
        className="cursor-pointer rounded-lg border border-orange-300 bg-card px-2.5 py-[5px] text-xs font-semibold text-orange-800 hover:bg-orange-100"
      >
        Re-run this stage
      </button>
    </div>
  );
}

/** Renders the AI-assistant action pills with their notes / scorecard. */
function AiActionRail() {
  const aiKey = useDemoStore((state) => state.aiKey);
  const toggleAiKey = useDemoStore((state) => state.toggleAiKey);
  const note = aiKey && aiKey !== "brand" ? AI_NOTES[aiKey] : undefined;

  return (
    <div className="mt-[18px]">
      <div className="mb-2 text-[11px] font-bold tracking-wide text-muted-foreground uppercase">
        Act on this document
      </div>
      <div className="flex flex-wrap gap-1.5">
        {AI_ACTIONS.map((action) => (
          <button
            key={action.key}
            onClick={() => toggleAiKey(action.key)}
            className={cn(
              "cursor-pointer rounded-full border px-[11px] py-[5px] text-xs font-semibold hover:border-primary hover:text-primary",
              aiKey === action.key
                ? "border-primary bg-indigo-50 text-primary"
                : "bg-card text-slate-700",
            )}
          >
            {action.label}
          </button>
        ))}
      </div>
      {note && (
        <div className="mt-2.5 rounded-[10px] border bg-slate-50 px-[13px] py-[11px] text-[12.5px] text-slate-700">
          {note}
        </div>
      )}
      {aiKey === "brand" && (
        <div className="mt-2.5 rounded-[10px] border bg-slate-50 px-[13px] py-3">
          <div className="mb-2 text-xs font-bold">Brand alignment</div>
          {SCORECARD.map((row) => (
            <div key={row.k} className="flex justify-between py-[3px] text-xs">
              <span className="text-muted-foreground">{row.k}</span>
              <span
                className={cn(
                  "font-bold",
                  row.tone === "good" ? "text-emerald-700" : "text-amber-700",
                )}
              >
                {row.v}
              </span>
            </div>
          ))}
          <div className="mt-1.5 rounded-[7px] bg-amber-100 px-2 py-1.5 text-[11.5px] text-amber-700">
            ⚠ &quot;pays for itself&quot; needs the cost-per-clean
            substantiation attached before publishing.
          </div>
        </div>
      )}
    </div>
  );
}

/** Renders the Evidence / Comments tab pair of the right-hand panel. */
function EvidencePanel() {
  const rightTab = useDemoStore((state) => state.rightTab);
  const setRightTab = useDemoStore((state) => state.setRightTab);

  return (
    <div className="mt-[18px] border-t border-slate-100 pt-3.5">
      <div className="mb-2.5 flex gap-1.5">
        <button
          onClick={() => setRightTab("evidence")}
          className={cn(
            "cursor-pointer rounded-[7px] px-2.5 py-[5px] text-xs font-semibold",
            rightTab === "evidence"
              ? "bg-slate-100 text-foreground"
              : "text-muted-foreground",
          )}
        >
          Evidence
        </button>
        <button
          onClick={() => setRightTab("comments")}
          className={cn(
            "cursor-pointer rounded-[7px] px-2.5 py-[5px] text-xs font-semibold",
            rightTab === "comments"
              ? "bg-slate-100 text-foreground"
              : "text-muted-foreground",
          )}
        >
          Comments · 2
        </button>
      </div>
      {rightTab === "evidence" ? (
        <div className="flex flex-col gap-2">
          {EVIDENCE.map((source) => (
            <div
              key={source.id}
              className="rounded-[10px] border px-3 py-2.5 hover:border-indigo-200"
            >
              <div className="flex items-center gap-1.5">
                <span className="rounded-[5px] bg-indigo-50 px-1.5 py-px text-[10.5px] font-bold text-primary">
                  {source.id}
                </span>
                <span className="text-[10.5px] font-semibold text-muted-foreground uppercase">
                  {source.type}
                </span>
              </div>
              <div className="mt-1 text-[12.5px] font-semibold">
                {source.title}
              </div>
              <div className="text-[11.5px] text-muted-foreground">
                {source.note}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="flex flex-col gap-2.5">
          <div className="flex gap-2">
            <div className="flex size-6 shrink-0 items-center justify-center rounded-full bg-amber-500 text-[11px] font-bold text-white">
              D
            </div>
            <div>
              <div className="text-xs">
                <strong>Dana</strong>{" "}
                <span className="text-slate-400">· 2h</span>
              </div>
              <div className="mt-0.5 text-[12.5px]">
                Can we lead with refill economics in the hero too, not just
                pillar 1?
              </div>
            </div>
          </div>
          <div className="flex gap-2">
            <div className="flex size-6 shrink-0 items-center justify-center rounded-full bg-slate-900 text-[11px] font-bold text-white">
              M
            </div>
            <div>
              <div className="text-xs">
                <strong>Maya</strong>{" "}
                <span className="text-slate-400">· 1h</span>
              </div>
              <div className="mt-0.5 text-[12.5px]">
                Agreed — flagged for the Plan stage.
              </div>
            </div>
          </div>
          <input
            placeholder="Add a comment…"
            className="rounded-lg border bg-slate-50 px-[11px] py-2 text-[12.5px]"
          />
        </div>
      )}
    </div>
  );
}

/** Renders the campaign Workspace: stepper, stage document, decision rail. */
export default function WorkspacePage() {
  const { slug } = useParams<{ slug: string }>();
  const stage = useDemoStore((state) => state.stage);
  const approved = useDemoStore((state) => state.approved);
  const reopened = useDemoStore((state) => state.reopened);
  const staleCleared = useDemoStore((state) => state.staleCleared);
  const created = useDemoStore((state) =>
    state.createdCampaigns.find((campaign) => campaign.slug === slug),
  );

  const fixture = campaignRows(approved).find((row) => row.slug === slug);
  if (!fixture && !created) {
    return (
      <main className="flex-1 overflow-y-auto px-4 py-6 md:px-8 md:py-7">
        <h1 className="text-[22px] font-bold tracking-tight">
          Campaign not found
        </h1>
        <p className="mt-1 text-[13px] text-muted-foreground">
          <Link href="/campaigns">← Back to campaigns</Link>
        </p>
      </main>
    );
  }

  const name = created ? created.name : fixture!.name;
  const status: Status = created ? "Draft" : fixture!.status;
  const statusFor = created
    ? createdStageStatus
    : (index: number) => stageStatus(index, approved, reopened, staleCleared);
  const subtitles = created
    ? CREATED_SUBTITLES
    : stageSubtitles(approved, reopened, staleCleared);

  const document =
    created && stage === 0 ? (
      <CreatedBriefDocument campaign={created} />
    ) : stage === STRATEGY_STAGE_INDEX ? (
      <StrategyDocument />
    ) : (
      <GenericStageDocument />
    );

  return (
    <main className="flex min-w-0 flex-1 flex-col overflow-hidden">
      <div className="border-b bg-card px-4 pt-3.5 md:px-6">
        <div className="flex items-center gap-2 text-[12.5px] text-muted-foreground">
          <Link
            href="/campaigns"
            className="text-muted-foreground no-underline hover:text-primary"
          >
            Campaigns
          </Link>
          <span>/</span>
          <span className="font-semibold text-foreground">{name}</span>
          <StatusPill status={status} />
        </div>
        <Stepper statusFor={statusFor} />
      </div>
      <div className="flex min-h-0 flex-1 flex-col overflow-auto lg:flex-row">
        <StageNav statusFor={statusFor} subtitles={subtitles} />
        <div className="flex-1 overflow-visible px-4 py-6 lg:min-w-[420px] lg:overflow-auto lg:px-7">
          {document}
        </div>
        <div className="w-full shrink-0 border-t bg-card p-4 lg:w-[312px] lg:overflow-auto lg:border-t-0 lg:border-l">
          {stage === STRATEGY_STAGE_INDEX &&
            (reopened ? (
              <ReopenedPanel />
            ) : approved ? (
              <ApprovedPanel />
            ) : (
              <DecisionPanel />
            ))}
          <AiActionRail />
          <EvidencePanel />
        </div>
      </div>
    </main>
  );
}
