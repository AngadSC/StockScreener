import Link from 'next/link';
import LoginForm from '@/components/auth/LoginForm';
import { sanitizeRedirectPath } from '@/lib/utils';

export default function LoginPage({
  searchParams,
}: {
  searchParams?: { redirect?: string | string[] };
}) {
  const redirectTo = sanitizeRedirectPath(searchParams?.redirect);
  const registerHref =
    redirectTo === '/screener'
      ? '/auth/register'
      : `/auth/register?redirect=${encodeURIComponent(redirectTo)}`;

  return (
    <div className="container-custom flex min-h-[calc(100vh-5rem)] items-center justify-center py-10">
      <div className="w-full max-w-md space-y-6">
        <LoginForm redirectTo={redirectTo} />
        <p className="text-center text-sm text-[var(--text-secondary)]">
          Don&apos;t have an account?{' '}
          <Link href={registerHref} className="deco-link">
            Create an account
          </Link>
        </p>
      </div>
    </div>
  );
}
