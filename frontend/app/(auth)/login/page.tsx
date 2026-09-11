"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { ShieldCheck, Eye, EyeOff, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { authApi } from "@/lib/api";
import { saveAuth } from "@/lib/auth";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("admin@sih.gov.in");
  const [password, setPassword] = useState("Admin@SIH2026");
  const [showPw, setShowPw] = useState(false);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    try {
      const { data } = await authApi.login(email, password);
      saveAuth(data.access_token, data.user);
      toast.success(`Welcome, ${data.user.full_name}`);
      router.push("/dashboard");
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Login failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-bg flex flex-col items-center justify-center px-4">
      {/* Background grid */}
      <div className="fixed inset-0 opacity-[0.03]"
        style={{ backgroundImage: "linear-gradient(#263450 1px,transparent 1px),linear-gradient(90deg,#263450 1px,transparent 1px)", backgroundSize: "40px 40px" }}
      />

      <div className="relative w-full max-w-md">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-xl bg-surface border border-bdr mb-4">
            <ShieldCheck className="w-7 h-7 text-accent" />
          </div>
          <h1 className="text-2xl font-bold text-ink tracking-tight">SIH Intelligence</h1>
          <p className="text-ink-2 text-sm mt-1">Social Media Analytics Platform</p>
          <div className="inline-flex items-center gap-1.5 mt-3 px-3 py-1 bg-accent/10 border border-accent/30 rounded-full">
            <span className="w-1.5 h-1.5 rounded-full bg-accent animate-pulse" />
            <span className="text-accent text-xs font-semibold tracking-wider uppercase">Demo Mode</span>
          </div>
        </div>

        {/* Card */}
        <div className="bg-surface border border-bdr rounded-xl p-8">
          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label className="block text-xs font-semibold text-ink-2 uppercase tracking-widest mb-2">
                Email Address
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                className="w-full bg-bg border border-bdr rounded-lg px-4 py-2.5 text-ink text-sm placeholder:text-ink-3 focus:outline-none focus:border-accent/60 transition-colors"
                placeholder="you@sih.gov.in"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-ink-2 uppercase tracking-widest mb-2">
                Password
              </label>
              <div className="relative">
                <input
                  type={showPw ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  className="w-full bg-bg border border-bdr rounded-lg px-4 py-2.5 pr-10 text-ink text-sm placeholder:text-ink-3 focus:outline-none focus:border-accent/60 transition-colors"
                  placeholder="••••••••"
                />
                <button
                  type="button"
                  onClick={() => setShowPw(!showPw)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-ink-3 hover:text-ink-2 transition-colors"
                >
                  {showPw ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-accent hover:bg-accent/90 text-white font-semibold py-2.5 px-4 rounded-lg text-sm transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
              {loading ? "Signing in…" : "Sign In"}
            </button>
          </form>

          <p className="mt-5 text-xs text-ink-3 text-center">
            Demo credentials are pre-filled above
          </p>
        </div>

        <p className="text-center text-xs text-ink-3 mt-6">
          Smart India Hackathon 2026 · AI Social Media Analytics
        </p>
      </div>
    </div>
  );
}
