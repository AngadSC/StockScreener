import fs from 'fs';
import path from 'path';
import matter from 'gray-matter';

const postsDir = path.join(process.cwd(), 'src/content/posts');

export type PostMeta = {
  slug: string;
  title: string;
  date: string;
  excerpt: string;
  tags: string[];
};

export type Post = PostMeta & {
  content: string;
};

export function getAllPosts(): PostMeta[] {
  const files = fs.readdirSync(postsDir);

  return files
    .filter((f) => f.endsWith('.mdx') || f.endsWith('.md'))
    .map((filename) => {
      const slug = filename.replace(/\.mdx?$/, '');
      const raw = fs.readFileSync(path.join(postsDir, filename), 'utf8');
      const { data } = matter(raw);

      return {
        slug,
        title: (data.title as string) ?? slug,
        date: (data.date as string) ?? '',
        excerpt: (data.excerpt as string) ?? '',
        tags: (data.tags as string[]) ?? [],
      };
    })
    .sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime());
}

export function getPostBySlug(slug: string): Post {
  for (const ext of ['.mdx', '.md']) {
    const fullPath = path.join(postsDir, `${slug}${ext}`);
    if (fs.existsSync(fullPath)) {
      const raw = fs.readFileSync(fullPath, 'utf8');
      const { data, content } = matter(raw);

      return {
        slug,
        title: (data.title as string) ?? slug,
        date: (data.date as string) ?? '',
        excerpt: (data.excerpt as string) ?? '',
        tags: (data.tags as string[]) ?? [],
        content,
      };
    }
  }

  throw new Error(`Post not found: ${slug}`);
}

export function formatPostDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });
}
