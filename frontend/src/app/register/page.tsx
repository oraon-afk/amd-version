import { RegisterForm } from "@/features/auth/components/RegisterForm";
import { AuthShowcase } from "@/components/auth/AuthShowcase";

export default function RegisterPage() {
  return (
    <main className="grid min-h-screen bg-background bg-app-radial text-foreground lg:grid-cols-[0.85fr_1.15fr]">
      <AuthShowcase mode="register" />
      <section className="flex items-center justify-center px-5 py-10">
        <RegisterForm />
      </section>
    </main>
  );
}
