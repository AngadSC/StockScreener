import type { Metadata } from 'next';
import Link from 'next/link';
import { getAllPosts, formatPostDate } from '@/lib/blog';

export const metadata: Metadata = {
  title: 'Blog — QuantorSignal',
  description:
    'Insights on stock screening, technical analysis, momentum trading, and market intelligence from the QuantorSignal team.',
};

export default function BlogIndexPage() {
  const posts = getAllPosts();

  return (
    <div className="container-custom py-10 md:py-16">
      <div className="mb-10">
        <div className="eyebrow">Blog</div>
        <h1 className="mt-3 text-3xl font-bold tracking-tight text-[var(--text-primary)] md:text-4xl">
          Market Insights
        </h1>
        <p className="mt-3 max-w-xl text-sm leading-7 text-[var(--text-secondary)]">
          Thoughts on screening, technical analysis, and the mechanics behind finding good setups.
        </p>
      </div>

      {posts.length === 0 ? (
        <div className="deco-panel p-8 text-center text-sm text-[var(--text-secondary)]">
          No posts yet — check back soon.
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {posts.map((post) => (
            <Link
              key={post.slug}
              href={`/blog/${post.slug}`}
              className="deco-panel card-hover group flex flex-col gap-4 p-6 transition-[border-color,box-shadow,transform] duration-200"
            >
              <div className="flex flex-wrap gap-2">
                {post.tags.map((tag) => (
                  <span
                    key={tag}
                    className="rounded-full border border-[var(--border-default)] px-2.5 py-0.5 text-[11px] font-medium tracking-wide text-[var(--text-tertiary)]"
                  >
                    {tag}
                  </span>
                ))}
              </div>

              <div className="flex-1">
                <h2 className="text-base font-semibold leading-snug text-[var(--text-primary)] transition-colors duration-[180ms] group-hover:text-[var(--accent)]">
                  {post.title}
                </h2>
                <p className="mt-2 text-sm leading-6 text-[var(--text-secondary)] line-clamp-3">
                  {post.excerpt}
                </p>
              </div>

              <div className="text-xs text-[var(--text-tertiary)]">{formatPostDate(post.date)}</div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
