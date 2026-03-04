"use client";

import Link from "next/link";
import { useAuth } from "@/hooks/use-auth";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import {
  BookOpen,
  Database,
  Lock,
  Share2,
  Zap,
  Users,
  Cloud,
  BarChart3,
} from "lucide-react";

export default function Home() {
  const { user } = useAuth();

  return (
    <div className="flex min-h-screen flex-col bg-gradient-to-b from-background to-secondary/10">
      {/* Navigation */}
      <nav className="border-b border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 sm:px-6">
          <div className="text-2xl font-bold text-primary">AudioSync</div>
          <div className="flex gap-2">
            {user ? (
              <Link href="/dashboard">
                <Button>Go to Dashboard</Button>
              </Link>
            ) : (
              <>
                <Link href="/login">
                  <Button variant="ghost">Sign In</Button>
                </Link>
                <Link href="/register">
                  <Button>Get Started</Button>
                </Link>
              </>
            )}
          </div>
        </div>
      </nav>

      <main className="flex-1">
        {/* Hero Section */}
        <section className="mx-auto max-w-6xl px-4 sm:px-6 py-20 sm:py-32">
          <div className="flex flex-col items-center text-center gap-8">
            <div className="space-y-4">
              <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold tracking-tight">
                Your Audible Library,{" "}
                <span className="text-primary">Your Storage</span>
              </h1>
              <p className="text-lg sm:text-xl text-muted-foreground max-w-2xl mx-auto leading-relaxed">
                Synchronize your Audible library to self-hosted storage. Download,
                decrypt, and share audiobooks with your family—all on your terms.
              </p>
            </div>

            <div className="flex flex-col sm:flex-row gap-4">
              {user ? (
                <Link href="/dashboard">
                  <Button size="lg" className="h-12 px-8">
                    Go to Dashboard
                  </Button>
                </Link>
              ) : (
                <>
                  <Link href="/register">
                    <Button size="lg" className="h-12 px-8">
                      Start Free
                    </Button>
                  </Link>
                  <Link href="/login">
                    <Button size="lg" variant="outline" className="h-12 px-8">
                      Sign In
                    </Button>
                  </Link>
                </>
              )}
            </div>
          </div>
        </section>

        {/* Features Section */}
        <section className="mx-auto max-w-6xl px-4 sm:px-6 py-20">
          <div className="text-center mb-16">
            <h2 className="text-3xl sm:text-4xl font-bold mb-4">
              Everything You Need
            </h2>
            <p className="text-muted-foreground text-lg max-w-2xl mx-auto">
              A complete solution for managing your audiobook library independently
            </p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
            {features.map((feature, idx) => (
              <Card key={idx} className="p-6 hover:border-primary/50 transition-colors">
                <feature.icon className="w-8 h-8 text-primary mb-4" />
                <h3 className="font-semibold mb-2">{feature.title}</h3>
                <p className="text-sm text-muted-foreground">{feature.description}</p>
              </Card>
            ))}
          </div>
        </section>

        {/* How It Works Section */}
        <section className="mx-auto max-w-6xl px-4 sm:px-6 py-20">
          <div className="text-center mb-16">
            <h2 className="text-3xl sm:text-4xl font-bold mb-4">
              Simple & Automated
            </h2>
            <p className="text-muted-foreground text-lg">
              Set up once, sync automatically
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-8">
            {steps.map((step, idx) => (
              <div key={idx} className="relative">
                <div className="flex flex-col items-center text-center gap-4">
                  <div className="flex h-12 w-12 items-center justify-center rounded-full bg-primary text-primary-foreground font-semibold">
                    {idx + 1}
                  </div>
                  <div>
                    <h3 className="font-semibold text-lg mb-2">{step.title}</h3>
                    <p className="text-muted-foreground">{step.description}</p>
                  </div>
                </div>
                {idx < steps.length - 1 && (
                  <div className="absolute top-6 -right-4 w-8 h-0.5 bg-border hidden md:block" />
                )}
              </div>
            ))}
          </div>
        </section>

        {/* Key Benefits Section */}
        <section className="mx-auto max-w-6xl px-4 sm:px-6 py-20">
          <div className="bg-card border border-border rounded-lg p-8 sm:p-12">
            <h2 className="text-3xl sm:text-4xl font-bold mb-12 text-center">
              Why AudioSync?
            </h2>

            <div className="grid md:grid-cols-2 gap-12">
              {benefits.map((benefit, idx) => (
                <div key={idx} className="flex gap-4">
                  <div className="flex-shrink-0">
                    <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
                      ✓
                    </div>
                  </div>
                  <div>
                    <h3 className="font-semibold mb-2">{benefit.title}</h3>
                    <p className="text-sm text-muted-foreground">{benefit.description}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* CTA Section */}
        <section className="mx-auto max-w-6xl px-4 sm:px-6 py-20">
          <div className="rounded-lg bg-gradient-to-r from-primary/10 to-primary/5 border border-primary/20 p-12 text-center">
            <h2 className="text-3xl sm:text-4xl font-bold mb-4">
              {user ? "Ready to manage your library?" : "Ready to take control?"}
            </h2>
            <p className="text-lg text-muted-foreground mb-8 max-w-2xl mx-auto">
              {user
                ? "Set up your Audible account and start syncing."
                : "Join thousands of users managing their audiobooks independently."}
            </p>
            {!user && (
              <Link href="/register">
                <Button size="lg" className="h-12 px-8">
                  Get Started Free
                </Button>
              </Link>
            )}
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="border-t border-border bg-background/50 mt-20">
        <div className="mx-auto max-w-6xl px-4 sm:px-6 py-12">
          <div className="text-center text-sm text-muted-foreground">
            <p>AudioSync © 2024. Self-hosted. Open source. Yours.</p>
          </div>
        </div>
      </footer>
    </div>
  );
}

const features = [
  {
    icon: BookOpen,
    title: "Full Library Sync",
    description: "Automatically download all your Audible books to local storage",
  },
  {
    icon: Lock,
    title: "Secure & Private",
    description: "Your credentials and data stay on your server. Complete control.",
  },
  {
    icon: Share2,
    title: "Family Sharing",
    description: "Share audiobooks with family members with granular permissions",
  },
  {
    icon: Cloud,
    title: "Self-Hosted",
    description: "Deploy on your own infrastructure. No vendor lock-in.",
  },
  {
    icon: Zap,
    title: "Auto-Sync",
    description: "Scheduled background jobs keep your library fresh and updated",
  },
  {
    icon: Database,
    title: "Deduplication",
    description: "Store each book once, share across multiple family members",
  },
  {
    icon: Users,
    title: "Multi-Tenant",
    description: "Support for multiple families, each with their own space",
  },
  {
    icon: BarChart3,
    title: "Decryption",
    description: "Automatically decrypt .aax files to open .m4b format",
  },
];

const steps = [
  {
    title: "Link Your Account",
    description: "Connect your Audible account securely to AudioSync",
  },
  {
    title: "Configure Storage",
    description: "Set up your self-hosted MinIO or S3-compatible storage",
  },
  {
    title: "Start Syncing",
    description: "Automatic daily sync keeps your library up to date",
  },
];

const benefits = [
  {
    title: "Own Your Data",
    description:
      "All audiobooks and metadata are stored on your own servers. You control everything.",
  },
  {
    title: "No Subscription Limits",
    description:
      "Unlimited downloads and storage. You only pay for the infrastructure you use.",
  },
  {
    title: "Family Access",
    description:
      "Build a shared library for your family. Grant access with granular permissions.",
  },
  {
    title: "Open Format",
    description:
      "Get DRM-free .m4b files that work with any audiobook player.",
  },
  {
    title: "Automated Workflow",
    description:
      "Set it and forget it. AudioSync runs scheduled syncs automatically.",
  },
  {
    title: "Full Control",
    description:
      "No ads, no tracking, no external dependencies. Complete privacy.",
  },
];
