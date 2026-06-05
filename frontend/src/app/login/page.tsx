import { LoginForm } from "@/features/auth/components/LoginForm";
import { AuthShowcase } from "@/components/auth/AuthShowcase";
import { CosmicBackground } from "@/components/layout/CosmicBackground";

export default function LoginPage() {
  return (
    <main className="relative grid min-h-screen bg-background bg-app-radial text-foreground lg:grid-cols-[0.92fr_1.08fr]">
      <CosmicBackground />
      <AuthShowcase mode="login" />
      <section className="relative z-10 flex items-center justify-center px-5 py-10">
        <LoginForm />
      </section>
    </main>
  );
}
