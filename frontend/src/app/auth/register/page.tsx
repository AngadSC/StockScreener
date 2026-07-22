import Link from 'next/link';
import RegisterForm from '@/components/auth/RegisterForm';
import { sanitizeRedirectPath } from '@/lib/utils';

export default function RegisterPage({
  searchParams,
}: {
  searchParams?: { redirect?: string | string[] };
}) {
  const redirectTo = sanitizeRedirectPath(searchParams?.redirect);
  const loginHref =
    redirectTo === '/screener'
      ? '/auth/login'
      : `/auth/login?redirect=${encodeURIComponent(redirectTo)}`;

  return (
    <div className="container-custom flex min-h-[calc(100vh-5rem)] items-center justify-center py-10">
      <div className="w-full max-w-md space-y-6">
        <RegisterForm redirectTo={redirectTo} />
        <p className="text-center text-sm text-[var(--text-secondary)]">
          Already have an account?{' '}
          <Link href={loginHref} className="deco-link">
            Sign In
          </Link>
        </p>
      </div>
    </div>
  );
}
