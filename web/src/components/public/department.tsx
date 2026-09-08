import {
  Container,
  Eyebrow,
  SectionHeading,
} from "@/components/public/section";

const SPECIALISTS = [
  {
    name: "Research",
    text: "Category, competitors and buying habits, grounded in your Brand DNA and honest about what is unknown.",
  },
  {
    name: "Brand strategy",
    text: "Positioning, messaging and the value proposition every campaign leans on.",
  },
  {
    name: "Performance planning",
    text: "Channel mix, spend allocation, placements and KPI targets, decided with the reasoning shown.",
  },
  {
    name: "Creative direction",
    text: "Concepts and briefs written against the placements and formats the plan chose.",
  },
  {
    name: "Asset prompts",
    text: "Generation prompts for each creative unit, following the brief, ready for your review.",
  },
];

/** Renders the five specialist stages the platform covers. */
export function Department() {
  return (
    <section aria-labelledby="department-heading">
      <Container className="py-24">
        <div className="grid items-end gap-6 md:grid-cols-2 md:gap-x-16">
          <div>
            <Eyebrow>Your marketing department</Eyebrow>
            <SectionHeading id="department-heading">
              Five specialists. One brief. Your sign-off.
            </SectionHeading>
          </div>
          <p className="text-[16.5px] leading-relaxed text-slate-600">
            Each stage is run by a specialist with the practice of that
            discipline built in. All of them work from the same Brand DNA and
            hand a written, reasoned recommendation to the next.
          </p>
        </div>
        <ol className="mt-14 grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
          {SPECIALISTS.map((specialist, index) => (
            <li
              key={specialist.name}
              className="flex min-h-[200px] flex-col gap-2.5 rounded-2xl border p-6 transition-[transform,box-shadow] duration-200 hover:-translate-y-0.5 hover:shadow-[0_16px_40px_-16px_rgba(15,23,42,0.2)]"
            >
              <span className="text-xs font-semibold tracking-[0.06em] text-primary uppercase">
                Stage {String(index + 1).padStart(2, "0")}
              </span>
              <h3 className="text-lg font-semibold tracking-[-0.015em]">
                {specialist.name}
              </h3>
              <p className="text-sm leading-normal text-slate-600">
                {specialist.text}
              </p>
            </li>
          ))}
        </ol>
      </Container>
    </section>
  );
}
