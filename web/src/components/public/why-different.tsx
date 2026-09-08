import {
  Container,
  Eyebrow,
  SectionHeading,
} from "@/components/public/section";

const POINTS = [
  {
    title: "Strategy before content",
    text: "Research, positioning and a channel plan exist before a single creative brief is written.",
  },
  {
    title: "Every recommendation says why",
    text: "Each decision shows the inputs it read, the reasoning it followed and the gaps it found.",
  },
  {
    title: "Nothing runs without approval",
    text: "Each decision stops at a gate until you say so. Send it back and it is redone against your note.",
  },
  {
    title: "Brand DNA authored by you",
    text: "Never scraped from your website. Your answers, in your words, kept to your business and editable any time.",
  },
];

/** Renders what sets We-OS apart from a content generator. */
export function WhyDifferent() {
  return (
    <section
      aria-labelledby="different-heading"
      className="bg-slate-900 text-white"
    >
      <Container className="grid gap-12 py-24 md:grid-cols-2 md:gap-x-24">
        <div>
          <Eyebrow className="text-indigo-300">Why it&apos;s different</Eyebrow>
          <SectionHeading id="different-heading" className="max-w-[16ch]">
            Not a content generator.
          </SectionHeading>
          <p className="mt-5 max-w-[44ch] text-[16.5px] leading-relaxed text-slate-300">
            A workflow that does the strategy work first and shows its
            reasoning, so what you approve is a decision, not a draft.
          </p>
        </div>
        <ol className="grid content-start gap-4 sm:grid-cols-2">
          {POINTS.map((point, index) => (
            <li
              key={point.title}
              className="rounded-2xl border border-white/10 bg-white/5 p-6"
            >
              <span className="text-xs font-semibold text-indigo-300">
                {String(index + 1).padStart(2, "0")}
              </span>
              <h3 className="mt-3 mb-2 text-lg font-semibold tracking-[-0.015em]">
                {point.title}
              </h3>
              <p className="text-[14.5px] leading-normal text-slate-300">
                {point.text}
              </p>
            </li>
          ))}
        </ol>
      </Container>
    </section>
  );
}
