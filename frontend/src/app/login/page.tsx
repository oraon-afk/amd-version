import { LoginForm } from "@/features/auth/components/LoginForm";
import { AuthShowcase } from "@/components/auth/AuthShowcase";

export default function LoginPage() {
  return (
    <main className="grid min-h-screen bg-background bg-app-radial text-foreground lg:grid-cols-[0.92fr_1.08fr]">
      <AuthShowcase mode="login" />
      <section className="flex items-center justify-center px-5 py-10">
        <LoginForm />
      </section>
    </main>
  );
}
