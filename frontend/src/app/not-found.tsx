import { ArrowLeft, Compass } from "lucide-react";
import { Eyebrow } from "@/components/ui/Eyebrow";
import { Button } from "@/components/ui/button";

export default function NotFound() {
  return (
    <main
      id="main-content"
      className="flex-1 flex items-center justify-center py-20 px-4 sm:px-6"
    >
      <div className="max-w-md w-full p-8 border border-[var(--rule)] bg-[var(--surface)] rounded-[4px] text-center">
        <Eyebrow step="ERR_404" className="justify-center mb-4">
          Signal Lost
        </Eyebrow>

        <div className="w-12 h-12 mx-auto mb-6 p-3 bg-[var(--paper)] text-[var(--ink-2)] rounded-[2px] flex items-center justify-center">
          <Compass className="w-6 h-6 stroke-[1.5]" aria-hidden="true" />
        </div>

        <h1
          className="text-4xl sm:text-5xl font-extrabold uppercase tracking-tight text-[var(--ink)] font-sans mb-3"
          style={{ fontStretch: "75%" }}
        >
          ROUTE NOT FOUND
        </h1>

        <p className="font-sans text-xs sm:text-sm text-[var(--ink-2)] leading-relaxed mb-8">
          The requested instrument path does not exist or has been relocated. Return to the primary scan console to classify waste items.
        </p>

        <Button
          href="/"
          variant="primary"
          size="md"
          icon={<ArrowLeft className="w-4 h-4" />}
          className="w-full"
        >
          Return to Scanner
        </Button>
      </div>
    </main>
  );
}
