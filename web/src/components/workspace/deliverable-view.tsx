"use client";

import type { ComponentProps } from "react";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";

import { StatusPill } from "@/components/ui/status-pill";
import type { DeliverableVersionSummary } from "@/lib/engine";
import { cn } from "@/lib/utils";

/**
 * The props `react-markdown` renders an element with.
 *
 * It hands every component the syntax-tree node the element came from, on top
 * of the element's own HTML props.
 */
type MarkdownProps<Tag extends keyof React.JSX.IntrinsicElements> =
  ComponentProps<Tag> & { node?: unknown };

/**
 * Drops the syntax-tree node from the props of a rendered element.
 *
 * The node is a renderer detail rather than an HTML attribute, so it must not
 * reach the element: spreading it would put a literal `node="[object Object]"`
 * into the markup of every heading, paragraph and cell. Done here once rather
 * than in each component below, so there is one place this is handled.
 *
 * Args:
 *   props: The props `react-markdown` supplied.
 *
 * Returns:
 *   The element's own HTML props, with the node removed.
 */
function withoutNode<Tag extends keyof React.JSX.IntrinsicElements>(
  props: MarkdownProps<Tag>,
): ComponentProps<Tag> {
  const rest = { ...props };
  delete rest.node;
  return rest as ComponentProps<Tag>;
}

/**
 * How each markdown element is styled where the deliverable is read.
 *
 * Written out element by element rather than left to a prose plugin: Tailwind
 * v4 rules out `@tailwindcss/typography` as a drop-in, and naming the classes
 * here keeps the deliverable looking like the rest of the workspace instead of
 * like a generic article.
 */
const MARKDOWN_COMPONENTS = {
  h1: (props: MarkdownProps<"h1">) => (
    <h1
      {...withoutNode(props)}
      className="mt-5 mb-2 text-[17px] font-bold tracking-tight first:mt-0"
    />
  ),
  h2: (props: MarkdownProps<"h2">) => (
    <h2
      {...withoutNode(props)}
      className="mt-5 mb-2 text-[15px] font-bold tracking-tight first:mt-0"
    />
  ),
  h3: (props: MarkdownProps<"h3">) => (
    <h3
      {...withoutNode(props)}
      className="mt-4 mb-1.5 text-[13.5px] font-bold first:mt-0"
    />
  ),
  h4: (props: MarkdownProps<"h4">) => (
    <h4
      {...withoutNode(props)}
      className="mt-4 mb-1.5 text-[13px] font-bold first:mt-0"
    />
  ),
  p: (props: MarkdownProps<"p">) => (
    <p {...withoutNode(props)} className="my-2" />
  ),
  ul: (props: MarkdownProps<"ul">) => (
    <ul {...withoutNode(props)} className="my-2 list-disc pl-5" />
  ),
  ol: (props: MarkdownProps<"ol">) => (
    <ol {...withoutNode(props)} className="my-2 list-decimal pl-5" />
  ),
  li: (props: MarkdownProps<"li">) => (
    <li {...withoutNode(props)} className="my-1" />
  ),
  strong: (props: MarkdownProps<"strong">) => (
    <strong {...withoutNode(props)} className="font-semibold text-slate-900" />
  ),
  em: (props: MarkdownProps<"em">) => (
    <em {...withoutNode(props)} className="italic" />
  ),
  blockquote: (props: MarkdownProps<"blockquote">) => (
    <blockquote
      {...withoutNode(props)}
      className="my-3 border-l-2 border-slate-300 pl-3 text-slate-600 italic"
    />
  ),
  a: (props: MarkdownProps<"a">) => (
    <a
      {...withoutNode(props)}
      target="_blank"
      rel="noreferrer noopener"
      className="text-primary underline underline-offset-2"
    />
  ),
  code: (props: MarkdownProps<"code">) => {
    /**
     * A fenced block keeps the renderer's `language-*` class and is left plain,
     * because the `pre` around it already carries the panel styling. Only
     * inline code — which arrives with no class — gets the pill.
     */
    const { className, ...rest } = withoutNode(props);
    return (
      <code
        {...rest}
        className={cn(
          "font-mono text-[12px]",
          className === undefined && "rounded bg-slate-100 px-1 py-0.5",
          className,
        )}
      />
    );
  },
  pre: (props: MarkdownProps<"pre">) => (
    <pre
      {...withoutNode(props)}
      className="my-3 overflow-x-auto rounded-lg bg-slate-100 p-3 font-mono text-[12px]"
    />
  ),
  hr: (props: MarkdownProps<"hr">) => (
    <hr {...withoutNode(props)} className="my-4 border-slate-200" />
  ),
  table: (props: MarkdownProps<"table">) => (
    <div className="my-3 overflow-x-auto">
      <table
        {...withoutNode(props)}
        className="w-full border-collapse text-left"
      />
    </div>
  ),
  th: (props: MarkdownProps<"th">) => (
    <th
      {...withoutNode(props)}
      className="border border-slate-200 bg-slate-50 px-2.5 py-1.5 font-semibold"
    />
  ),
  td: (props: MarkdownProps<"td">) => (
    <td
      {...withoutNode(props)}
      className="border border-slate-200 px-2.5 py-1.5"
    />
  ),
};

/**
 * Renders a deliverable's markdown as the business owner reads it.
 *
 * The engine writes markdown, and the interface shows it whole. Nothing is
 * summarised or truncated: the decision at the gate is about this document, so
 * hiding part of it would ask for a decision on something the person cannot see.
 *
 * The markdown is rendered rather than shown as source, because a gate asks the
 * owner to read a document and `##` and `**` left in place make that harder.
 * Deliverable content is model-written, so no `rehype-raw` is configured and any
 * HTML in the source stays inert text rather than becoming markup.
 *
 * Args:
 *   content: The deliverable's full markdown.
 */
export function DeliverableContent({ content }: { content: string }) {
  return (
    <article
      aria-label="Deliverable"
      className="rounded-xl border bg-card px-[22px] py-5 text-[13.5px] leading-relaxed text-slate-800"
    >
      <Markdown remarkPlugins={[remarkGfm]} components={MARKDOWN_COMPONENTS}>
        {content}
      </Markdown>
    </article>
  );
}

/**
 * Renders the banner marking a deliverable as resting on a superseded decision.
 *
 * The re-run control lives here because staleness is the owner's to resolve:
 * the flag and the one action that clears it belong together, and nothing
 * re-runs until they ask for it (ADR-0015).
 *
 * Args:
 *   onRerun: Starts a run to bring the stage up to date.
 *   pending: Whether a re-run is already in flight.
 */
export function StaleBanner({
  onRerun,
  pending,
}: {
  onRerun: () => void;
  pending: boolean;
}) {
  return (
    <div
      role="status"
      className="mb-4 flex flex-wrap items-center gap-2 rounded-xl border border-orange-200 bg-orange-50 px-4 py-3"
    >
      <StatusPill status="Stale" />
      <span className="flex-1 text-[12.5px] text-orange-900">
        Built on a decision that has since been re-opened. Re-run this stage to
        bring it up to date — it will not update on its own.
      </span>
      <button
        onClick={onRerun}
        disabled={pending}
        className="cursor-pointer rounded-lg border border-orange-300 bg-card px-2.5 py-[5px] text-xs font-semibold text-orange-800 hover:bg-orange-100 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {pending ? "Starting…" : "Re-run this stage"}
      </button>
    </div>
  );
}

/**
 * Renders a deliverable's version history, newest first.
 *
 * Each entry names the feedback that produced it and whether that came from a
 * person or the QA reviewer, so the history explains itself months later
 * (ADR-0015). Selecting a version shows it, which is how two versions are
 * compared.
 *
 * Args:
 *   versions: The version summaries, newest first.
 *   selected: The version currently shown.
 *   onSelect: Shows a version.
 */
export function VersionHistory({
  versions,
  selected,
  onSelect,
}: {
  versions: DeliverableVersionSummary[];
  selected: number | null;
  onSelect: (version: number) => void;
}) {
  if (versions.length === 0) return null;

  return (
    <section aria-label="Version history" className="mt-[18px]">
      <div className="mb-2 text-[11px] font-bold tracking-wide text-muted-foreground uppercase">
        Version history
      </div>
      <ol className="flex flex-col gap-1.5">
        {versions.map((version) => (
          <li key={version.version}>
            <button
              onClick={() => onSelect(version.version)}
              aria-current={selected === version.version ? "true" : undefined}
              className={cn(
                "w-full cursor-pointer rounded-[10px] border px-3 py-2.5 text-left hover:border-indigo-200",
                selected === version.version && "border-primary bg-indigo-50",
              )}
            >
              <div className="flex items-center gap-1.5">
                <span className="text-[12.5px] font-bold">
                  v{version.version}
                </span>
                <span className="text-[11px] text-muted-foreground">
                  {new Date(version.created_at).toLocaleString()}
                </span>
              </div>
              <div className="mt-0.5 text-[12px] text-slate-700">
                {version.feedback
                  ? `${sourceLabel(version.feedback_source)}: ${version.feedback}`
                  : "First draft — nothing prompted it."}
              </div>
            </button>
          </li>
        ))}
      </ol>
    </section>
  );
}

/**
 * Names who asked for a revision, in the operator's terms.
 *
 * Args:
 *   source: The engine's feedback source.
 *
 * Returns:
 *   Who the feedback came from.
 */
function sourceLabel(source: string | null): string {
  if (source === "human") return "You asked";
  if (source === "reviewer") return "Guardrail review";
  return "Revised";
}
