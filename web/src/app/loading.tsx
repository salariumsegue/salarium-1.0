export default function Loading() {
  return (
    <main id="main-content" className="site-main">
      <div className="site-container site-section">
        <div className="animate-pulse">
          <div className="h-3 w-40 bg-emerald-300/20" />
          <div className="mt-6 h-14 max-w-2xl bg-white/8" />
          <div className="mt-4 h-5 max-w-xl bg-white/5" />
          <div className="mt-12 grid gap-4 md:grid-cols-4">{Array.from({ length: 4 }).map((_, index) => <div key={index} className="h-32 border border-white/8 bg-white/[0.015]" />)}</div>
        </div>
      </div>
    </main>
  );
}
