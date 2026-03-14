export default function PrivacyPage() {
  return (
    <div className="container-custom py-10">
      <section className="deco-panel max-w-3xl p-6 md:p-8">
        <div className="eyebrow">Privacy Policy</div>
        <h1 className="mt-3">Data Handling</h1>
        <p className="mt-4 text-sm leading-7 text-[var(--text-secondary)]">
          QuantorSignal stores account and watchlist data necessary to operate the application and
          improve reliability. Authentication state is used only to secure user-specific features.
        </p>
        <p className="mt-4 text-sm leading-7 text-[var(--text-secondary)]">
          Market data shown in the product may come from third-party providers and should be treated
          as reference data rather than a sole basis for financial decisions.
        </p>
      </section>
    </div>
  );
}
