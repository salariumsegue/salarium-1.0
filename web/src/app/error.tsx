"use client";

import Link from "next/link";
import { useEffect } from "react";

export default function ErrorPage({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <main id="main-content" className="site-main">
      <section className="page-section flex min-h-[62vh] items-center">
        <div className="max-w-2xl">
          <p className="eyebrow text-red-300">Page error</p>
          <h1 className="mt-5 text-5xl font-semibold tracking-tight sm:text-7xl">This page couldn&apos;t load.</h1>
          <p className="mt-6 max-w-xl text-base leading-7 text-white/45">
            Try loading the page again. If the problem continues, return home and try another section.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <button type="button" className="button-primary" onClick={reset}>Try again <span aria-hidden="true">→</span></button>
            <Link href="/" className="button-secondary">Go to home</Link>
          </div>
          {error.digest && <p className="mt-6 font-mono text-[10px] tracking-[0.12em] text-white/20">ERROR DIGEST {error.digest}</p>}
        </div>
      </section>
    </main>
  );
}
