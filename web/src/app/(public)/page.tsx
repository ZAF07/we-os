import { Department } from "@/components/public/department";
import { Faq } from "@/components/public/faq";
import { FinalCall } from "@/components/public/final-call";
import { Hero } from "@/components/public/hero";
import { HowItWorks } from "@/components/public/how-it-works";
import { Loop } from "@/components/public/loop";
import { WhyDifferent } from "@/components/public/why-different";

/**
 * Renders the Landing: what We-OS is, for a visitor deciding whether it is for
 * them.
 *
 * A static server component with no engine call and no session, so it is fast
 * and can never show an engine error. The story runs in one order — what it
 * promises, how the work runs, who does it, why it is different, what people
 * ask, and the way in — and every claim is true of the product today. What it
 * costs is the Pricing page's job, one link away in the top bar and footer.
 */
export default function LandingPage() {
  return (
    <main>
      <Hero />
      <Loop />
      <HowItWorks />
      <Department />
      <WhyDifferent />
      <Faq />
      <FinalCall />
    </main>
  );
}
