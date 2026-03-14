import Link from 'next/link';

export default function ContactPage() {
  return (
    <div className="container-custom py-10">
      <section className="deco-panel max-w-3xl p-6 md:p-8">
        <div className="eyebrow">Contact</div>
        <h1 className="mt-3">Support</h1>
        <p className="mt-4 text-sm leading-7 text-[var(--text-secondary)]">
          For product questions, bug reports, or account issues, use the contact channel configured
          for your deployment.
        </p>
        <p className="mt-4 text-sm leading-7 text-[var(--text-secondary)]">
          If you do not have a support inbox configured yet, start with{' '}
          <Link
            href="mailto:support@quantorsignal.com"
            className="text-[var(--accent)] transition-colors duration-[180ms] hover:text-[var(--accent-hover)]"
          >
            support@quantorsignal.com
          </Link>
          .
        </p>
      </section>
    </div>
  );
}
