import type { Metadata } from 'next';
import Link from 'next/link';
import { notFound } from 'next/navigation';
import { MDXRemote } from 'next-mdx-remote/rsc';
import { getAllPosts, getPostBySlug, formatPostDate } from '@/lib/blog';

type Props = {
  params: { slug: string };
};

export async function generateStaticParams() {
  return getAllPosts().map((post) => ({ slug: post.slug }));
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  try {
    const post = getPostBySlug(params.slug);
    return {
      title: `${post.title} — QuantorSignal`,
      description: post.excerpt,
      openGraph: {
        title: post.title,
        description: post.excerpt,
        type: 'article',
        publishedTime: post.date,
        tags: post.tags,
      },
    };
  } catch {
    return {};
  }
}

export default function BlogPostPage({ params }: Props) {
  let post;
  try {
    post = getPostBySlug(params.slug);
  } catch {
    notFound();
  }

  return (
    <div className="container-custom py-10 md:py-16">
      <div className="mx-auto max-w-2xl">
        <Link
          href="/blog"
          className="mb-8 inline-flex items-center gap-2 text-sm text-[var(--text-secondary)] transition-colors duration-[180ms] hover:text-[var(--text-primary)]"
        >
          ← All posts
        </Link>

        <div className="mt-6 flex flex-wrap gap-2">
          {post.tags.map((tag) => (
            <span
              key={tag}
              className="rounded-full border border-[var(--border-default)] px-2.5 py-0.5 text-[11px] font-medium tracking-wide text-[var(--text-tertiary)]"
            >
              {tag}
            </span>
          ))}
        </div>

        <h1 className="mt-4 text-3xl font-bold leading-tight tracking-tight text-[var(--text-primary)] md:text-4xl">
          {post.title}
        </h1>

        <p className="mt-2 text-sm text-[var(--text-tertiary)]">{formatPostDate(post.date)}</p>

        <div className="blog-prose mt-10">
          <MDXRemote source={post.content} />
        </div>
      </div>
    </div>
  );
}
