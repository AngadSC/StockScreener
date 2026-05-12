import { ExternalLink } from 'lucide-react';

import type { AIReportOutput, NewsArticle } from '@/types/ai';

interface AIReportNewsSectionProps {
  report: AIReportOutput;
  newsSources?: NewsArticle[];
}

function getArticleHeadline(article: NewsArticle) {
  return article.headline ?? article.title ?? article.url ?? 'Source article';
}

function formatNewsTag(value?: string) {
  return value?.replace(/[_-]+/g, ' ').replace(/\b\w/g, (letter) => letter.toUpperCase());
}

export default function AIReportNewsSection({
  report,
  newsSources = [],
}: AIReportNewsSectionProps) {
  return (
    <section className="deco-panel p-6 md:p-7">
      <div className="eyebrow">News</div>
      <h2 className="heading-lg mt-2 text-[var(--text-primary)]">Market Context</h2>

      <p className="mt-5 max-w-[80ch] whitespace-pre-line text-sm leading-7 text-[var(--text-secondary)]">
        {report.news_summary}
      </p>

      {newsSources.length > 0 ? (
        <div className="mt-6 border-t border-[var(--border-subtle)] pt-5">
          <h3 className="heading-sm text-[var(--text-primary)]">Sources</h3>
          <div className="mt-3 space-y-3">
            {newsSources.map((article) => {
              const headline = getArticleHeadline(article);

              const Tag = article.url ? 'a' : 'div';
              const linkProps = article.url
                ? { href: article.url, rel: 'noreferrer', target: '_blank' }
                : {};

              return (
                <Tag
                  key={`${headline}-${article.url ?? article.source ?? ''}`}
                  className="group flex items-start justify-between gap-4 rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--bg-surface-2)] p-4 transition-[border-color,background,color] duration-[180ms] hover:border-[var(--accent)] hover:bg-[var(--accent-subtle)]"
                  {...linkProps}
                >
                  <span className="min-w-0">
                    <span className="block text-sm font-medium leading-6 text-[var(--text-primary)]">
                      {headline}
                    </span>
                    {article.source ? (
                      <span className="mt-1 block text-xs text-[var(--text-tertiary)]">
                        {article.source}
                      </span>
                    ) : null}
                    <span className="mt-2 flex flex-wrap gap-2">
                      {[article.event_type, article.sentiment, article.materiality].filter(Boolean).map((value) => (
                        <span
                          key={value}
                          className="rounded-full border border-[var(--border-subtle)] px-2 py-0.5 text-[11px] text-[var(--text-tertiary)]"
                        >
                          {formatNewsTag(value)}
                        </span>
                      ))}
                    </span>
                    {article.why_it_matters ? (
                      <span className="mt-2 block text-xs leading-5 text-[var(--text-secondary)]">
                        {article.why_it_matters}
                      </span>
                    ) : null}
                  </span>
                  <ExternalLink className="mt-1 h-4 w-4 shrink-0 text-[var(--text-tertiary)] transition-colors duration-[180ms] group-hover:text-[var(--accent)]" />
                </Tag>
              );
            })}
          </div>
        </div>
      ) : null}
    </section>
  );
}
