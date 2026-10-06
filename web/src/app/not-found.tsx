import Link from "next/link";

export default function NotFound() {
  return (
    <main id="main-content" className="site-main">
      <section className="page-section flex min-h-[62vh] items-center">
        <div className="max-w-2xl">
          <p className="eyebrow text-red-300">404 / Page not found</p>
          <h1 className="mt-5 text-5xl font-semibold tracking-tight sm:text-7xl">That page isn&apos;t here.</h1>
          <p className="mt-6 max-w-xl text-base leading-7 text-white/45">
            The link may be old, or the address may be wrong. Go back to the home page or browse the research index.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link href="/" className="button-primary">Go to home <span aria-hidden="true">→</span></Link>
            <Link href="/research" className="button-secondary">Browse research</Link>
          </div>
        </div>
      </section>
    </main>
  );
}
