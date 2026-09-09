import { ChevronDown } from "lucide-react";

import {
  Container,
  Eyebrow,
  SectionHeading,
} from "@/components/public/section";

const QUESTIONS = [
  {
    question: "What is a credit?",
    answer:
      "What your business spends on generation. Each stage that runs uses some, heavier stages use more, and every tier grants a fresh set each month. Home shows how many are left and where they went, per campaign.",
  },
  {
    question: "Do I need marketing knowledge?",
    answer:
      "No. You need to know your business. The questionnaire asks about that in plain language; the practice of each discipline is built into the stage that needs it, and every recommendation explains itself.",
  },
  {
    question: "Does We-OS post for me?",
    answer:
      "Not yet. Today the workflow ends at an approved plan, creative briefs and asset prompts, all yours to use. Publishing to platforms is on the roadmap.",
  },
  {
    question: "Is my data private?",
    answer:
      "Yes. Every business's data is isolated to that business: your Brand DNA, campaigns and decisions are read only by your own stages. Nothing is scraped from your website and nothing is shared between businesses.",
  },
  {
    question: "What happens when credits run out?",
    answer:
      "Billable work pauses until the next month's credits arrive, or until you move to a higher tier. Nothing you have approved is lost, and everything you can read stays readable.",
  },
];

/**
 * Renders the questions people ask before paying, with honest answers.
 *
 * One component for the Landing, Pricing and Get Started, so the answers — in
 * particular that nothing is published yet — are the same wherever they are
 * read.
 */
export function Faq() {
  return (
    <section
      id="faq"
      aria-labelledby="faq-heading"
      className="scroll-mt-(--top-bar-height)"
    >
      <Container className="grid gap-10 py-24 md:grid-cols-[minmax(0,1fr)_minmax(0,1.6fr)] md:gap-x-24">
        <div>
          <Eyebrow>Questions</Eyebrow>
          <SectionHeading id="faq-heading" className="max-w-[16ch]">
            The ones people ask before paying.
          </SectionHeading>
        </div>
        <div className="flex flex-col gap-2.5">
          {QUESTIONS.map(({ question, answer }) => (
            <details
              key={question}
              className="group rounded-[14px] border bg-card px-[22px]"
            >
              <summary className="flex cursor-pointer list-none items-center justify-between gap-4 py-5 text-[16.5px] font-semibold tracking-[-0.01em] [&::-webkit-details-marker]:hidden">
                {question}
                <ChevronDown
                  aria-hidden="true"
                  className="size-[18px] shrink-0 text-primary transition-transform duration-200 group-open:rotate-180"
                />
              </summary>
              <p className="pb-[22px] text-[15px] leading-relaxed text-slate-600">
                {answer}
              </p>
            </details>
          ))}
        </div>
      </Container>
    </section>
  );
}
