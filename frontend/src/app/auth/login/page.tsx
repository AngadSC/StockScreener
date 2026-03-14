import Link from 'next/link';
import LoginForm from '@/components/auth/LoginForm';

export default function LoginPage() {
  return (
    <div className="container-custom flex min-h-[calc(100vh-5rem)] items-center justify-center py-10">
      <div className="w-full max-w-md space-y-6">
        <LoginForm />
        <p className="text-center text-sm text-muted-foreground">
          Don't have an account?{' '}
          <Link href="/auth/register" className="deco-link">
            Create an account
          </Link>
        </p>
      </div>
    </div>
  );
}
