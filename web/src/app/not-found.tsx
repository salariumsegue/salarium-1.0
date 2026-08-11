import Link from "next/link";

export default function NotFound() {
  return (
    <main id="main-content" className="site-main">
      <section className="page-section flex min-h-[62vh] items-center">
        <div className="max-w-2xl">
          <p className="eyebrow text-red-300">404 / Unmapped route</p>
          <h1 className="mt-5 text-5xl font-semibold tracking-tight sm:text-7xl">The research path ends here.</h1>
          <p className="mt-6 max-w-xl text-base leading-7 text-white/45">
            This route is not part of the Salarium release surface. Return to the governed overview or inspect the current research record.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link href="/" className="button-primary">Return to overview <span aria-hidden="true">→</span></Link>
            <Link href="/research" className="button-secondary">Open research record</Link>
          </div>
        </div>
      </section>
    </main>
  );
}
