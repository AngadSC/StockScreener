import Link from 'next/link';
import RegisterForm from '@/components/auth/RegisterForm';

export default function RegisterPage() {
  return (
    <div className="container-custom flex min-h-[calc(100vh-5rem)] items-center justify-center py-10">
      <div className="w-full max-w-md space-y-6">
        <RegisterForm />
        <p className="text-center text-sm text-muted-foreground">
          Already have an account?{' '}
          <Link href="/auth/login" className="deco-link">
            Login
          </Link>
        </p>
      </div>
    </div>
  );
}
