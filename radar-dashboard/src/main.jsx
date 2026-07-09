import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  AlertTriangle,
  Check,
  Clock,
  Download,
  ExternalLink,
  LogOut,
  Mail,
  Play,
  RefreshCw,
  Search,
} from "lucide-react";
import { apiFetch, authConfigured, supabase } from "./auth";
import "./styles.css";

const navItems = [
  { id: "dashboard", label: "Dashboard" },
  { id: "contacts", label: "Contacts" },
  { id: "health", label: "Health" },
];

const sourceClasses = {
  career_page: "bg-blue-50 text-blue-700 ring-blue-200",
  linkedin: "bg-indigo-50 text-indigo-700 ring-indigo-200",
  facebook: "bg-slate-100 text-slate-700 ring-slate-200",
};

function App() {
  const [session, setSession] = useState(null);
  const [authLoading, setAuthLoading] = useState(true);
  const [activeView, setActiveView] = useState("dashboard");
  const [backendDown, setBackendDown] = useState(false);

  useEffect(() => {
    if (!supabase) {
      setAuthLoading(false);
      return undefined;
    }
    supabase.auth.getSession().then(({ data }) => {
      setSession(data.session);
      setAuthLoading(false);
    });
    const { data } = supabase.auth.onAuthStateChange((_event, nextSession) => setSession(nextSession));
    return () => data.subscription.unsubscribe();
  }, []);

  if (authLoading) return <FullPageMessage message="Loading secure session..." />;
  if (!authConfigured) return <FullPageMessage message="Dashboard authentication is not configured." />;
  if (!session) return <Login />;

  return (
    <div className="min-h-screen bg-[#f7f8fa] text-ink-950">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-7xl flex-col gap-3 px-4 py-4 sm:flex-row sm:items-center sm:justify-between lg:px-6">
          <div>
            <h1 className="text-xl font-semibold tracking-normal">Internship Radar</h1>
            <p className="text-sm text-ink-600">Private opportunity monitor</p>
          </div>
          <div className="flex items-center gap-2">
            <nav className="flex rounded-md border border-slate-200 bg-slate-50 p-1">
              {navItems.map((item) => (
              <button
                key={item.id}
                type="button"
                onClick={() => setActiveView(item.id)}
                className={`rounded px-3 py-1.5 text-sm font-medium transition ${
                  activeView === item.id
                    ? "bg-white text-ink-950 shadow-sm"
                    : "text-ink-600 hover:text-ink-950"
                }`}
              >
                {item.label}
              </button>
              ))}
            </nav>
            <button
              type="button"
              onClick={() => supabase.auth.signOut()}
              className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-slate-200 bg-white text-ink-600 hover:bg-slate-50"
              title="Sign out"
              aria-label="Sign out"
            >
              <LogOut className="h-4 w-4" />
            </button>
          </div>
        </div>
      </header>

      {backendDown && (
        <div className="border-b border-red-200 bg-red-50 px-4 py-3 text-sm font-medium text-red-800">
          <div className="mx-auto flex max-w-7xl items-center gap-2 lg:px-6">
            <AlertTriangle className="h-4 w-4" />
            Cannot reach backend. Dashboard data may be stale.
          </div>
        </div>
      )}

      <main className="mx-auto max-w-7xl px-4 py-6 lg:px-6">
        {activeView === "dashboard" && <Dashboard onBackendStatus={setBackendDown} />}
        {activeView === "contacts" && <Contacts onBackendStatus={setBackendDown} />}
        {activeView === "health" && <Health onBackendStatus={setBackendDown} />}
      </main>
    </div>
  );
}

function Login() {
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  async function signIn(event) {
    event.preventDefault();
    setBusy(true);
    setMessage("");
    const { error } = await supabase.auth.signInWithOtp({
      email,
      options: { emailRedirectTo: window.location.origin },
    });
    setMessage(error ? error.message : "Check your email for the secure sign-in link.");
    setBusy(false);
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-[#f7f8fa] px-4">
      <form onSubmit={signIn} className="w-full max-w-sm rounded-md border border-slate-200 bg-white p-6 shadow-soft">
        <h1 className="text-xl font-semibold">Internship Radar</h1>
        <p className="mt-1 text-sm text-ink-600">Sign in with an approved email address.</p>
        <label className="mt-5 block text-sm font-medium">
          Email
          <input
            type="email"
            required
            autoComplete="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            className="mt-2 w-full rounded-md border border-slate-200 px-3 py-2 outline-none ring-blue-100 focus:border-blue-400 focus:ring-4"
          />
        </label>
        <button
          type="submit"
          disabled={busy}
          className="mt-4 w-full rounded-md bg-ink-950 px-3 py-2 text-sm font-medium text-white hover:bg-ink-800 disabled:opacity-60"
        >
          {busy ? "Sending..." : "Send sign-in link"}
        </button>
        {message && <p className="mt-3 text-sm text-ink-600">{message}</p>}
      </form>
    </main>
  );
}

function FullPageMessage({ message }) {
  return (
    <main className="flex min-h-screen items-center justify-center bg-[#f7f8fa] p-6 text-sm text-ink-600">
      {message}
    </main>
  );
}

function Dashboard({ onBackendStatus }) {
  const { data, loading, error, refetch, setData } = useApi("/api/postings", onBackendStatus);
  const [statusFilter, setStatusFilter] = useState("all");
  const [query, setQuery] = useState("");

  const postings = Array.isArray(data) ? data : [];
  const filteredPostings = useMemo(() => {
    return postings
      .filter((posting) => {
        if (statusFilter === "new") return !Boolean(posting.applied);
        if (statusFilter === "applied") return Boolean(posting.applied);
        return true;
      })
      .filter((posting) => posting.company?.toLowerCase().includes(query.toLowerCase()))
      .sort((a, b) => new Date(b.date_found || 0) - new Date(a.date_found || 0));
  }, [postings, statusFilter, query]);

  const counts = useMemo(() => {
    const applied = postings.filter((posting) => Boolean(posting.applied)).length;
    return { total: postings.length, new: postings.length - applied, applied };
  }, [postings]);

  async function markApplied(postingId) {
    try {
      const response = await apiFetch(`/api/postings/${postingId}/apply`, { method: "POST" });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      setData((current) =>
        current.map((posting) => (posting.id === postingId ? { ...posting, applied: true } : posting)),
      );
    } catch (err) {
      onBackendStatus(true);
      alert(`Could not mark posting as applied: ${err.message}`);
    }
  }

  return (
    <section className="space-y-5">
      <Toolbar title="Postings" onRefresh={refetch}>
        <ManualScan onComplete={refetch} />
      </Toolbar>
      <SummaryStrip counts={counts} />

      <div className="flex flex-col gap-3 rounded-md border border-slate-200 bg-white p-3 shadow-soft md:flex-row md:items-center md:justify-between">
        <SegmentedControl value={statusFilter} onChange={setStatusFilter} />
        <SearchBox value={query} onChange={setQuery} placeholder="Filter by company" />
      </div>

      {loading && <SkeletonRows />}
      {error && <InlineError message={error} />}
      {!loading && !error && filteredPostings.length === 0 && (
        <EmptyState title="No postings yet" message="Check back after the next scan." />
      )}
      {!loading && !error && filteredPostings.length > 0 && (
        <PostingsTable postings={filteredPostings} onApply={markApplied} />
      )}
    </section>
  );
}

function ManualScan({ onComplete }) {
  const [busy, setBusy] = useState(false);

  async function runScan() {
    setBusy(true);
    try {
      const response = await apiFetch("/api/scans", { method: "POST" });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      await onComplete();
    } catch (error) {
      alert(`Scan could not complete: ${error.message}`);
    } finally {
      setBusy(false);
    }
  }

  return (
    <button
      type="button"
      disabled={busy}
      onClick={runScan}
      className="inline-flex items-center gap-2 rounded-md bg-ink-950 px-3 py-2 text-sm font-medium text-white hover:bg-ink-800 disabled:opacity-60"
    >
      <Play className="h-4 w-4" />
      {busy ? "Scanning..." : "Scan now"}
    </button>
  );
}

function Contacts({ onBackendStatus }) {
  const { data, loading, error, refetch } = useApi("/api/contacts", onBackendStatus);
  const [query, setQuery] = useState("");
  const contacts = Array.isArray(data) ? data : [];
  const filteredContacts = contacts.filter((contact) =>
    contact.company?.toLowerCase().includes(query.toLowerCase()),
  );

  function exportCsv() {
    const headers = ["Company", "Email", "Source page", "Date scraped"];
    const rows = filteredContacts.map((contact) => [
      contact.company,
      contact.email,
      contact.source_page,
      formatDate(contact.date_scraped),
    ]);
    const csv = [headers, ...rows].map((row) => row.map(csvEscape).join(",")).join("\n");
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "internship-radar-contacts.csv";
    link.click();
    URL.revokeObjectURL(url);
  }

  return (
    <section className="space-y-5">
      <Toolbar title="Contacts" onRefresh={refetch}>
        <button
          type="button"
          onClick={exportCsv}
          className="inline-flex items-center gap-2 rounded-md bg-ink-950 px-3 py-2 text-sm font-medium text-white hover:bg-ink-800"
        >
          <Download className="h-4 w-4" />
          Export CSV
        </button>
      </Toolbar>

      <div className="rounded-md border border-slate-200 bg-white p-3 shadow-soft">
        <SearchBox value={query} onChange={setQuery} placeholder="Filter by company" />
      </div>

      {loading && <SkeletonRows />}
      {error && <InlineError message={error} />}
      {!loading && !error && filteredContacts.length === 0 && (
        <EmptyState title="No contacts yet" message="Run contacts update, then refresh this page." />
      )}
      {!loading && !error && filteredContacts.length > 0 && <ContactsTable contacts={filteredContacts} />}
    </section>
  );
}

function Health({ onBackendStatus }) {
  const { data, loading, error, refetch } = useApi("/api/health", onBackendStatus);
  const flagged = new Set(data?.flagged_companies || []);
  const status = healthStatus(data?.last_scan_time);
  const companies = Object.entries(data?.per_company_posting_counts || {});

  return (
    <section className="space-y-5">
      <Toolbar title="System Health" onRefresh={refetch} />
      {loading && <SkeletonRows />}
      {error && <InlineError message={error} />}
      {!loading && !error && data && (
        <>
          <div className="grid gap-4 md:grid-cols-2">
            <div className="rounded-md border border-slate-200 bg-white p-4 shadow-soft">
              <div className="flex items-center gap-3">
                <span className={`h-3 w-3 rounded-full ${status.dot}`} />
                <div>
                  <p className="text-sm font-medium text-ink-600">Last successful scan</p>
                  <p className="text-lg font-semibold">{formatDate(data.last_scan_time) || "Unknown"}</p>
                </div>
              </div>
            </div>
            <div className="rounded-md border border-slate-200 bg-white p-4 shadow-soft">
              <div className="flex items-center gap-3">
                <Mail className="h-5 w-5 text-ink-600" />
                <div>
                  <p className="text-sm font-medium text-ink-600">Last email sent</p>
                  <p className="text-lg font-semibold">{formatDate(data.last_email_sent_time) || "Never"}</p>
                </div>
              </div>
            </div>
          </div>
          <HealthTable companies={companies} flagged={flagged} />
        </>
      )}
    </section>
  );
}

function Toolbar({ title, onRefresh, children }) {
  return (
    <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
      <h2 className="text-lg font-semibold">{title}</h2>
      <div className="flex items-center gap-2">
        {children}
        <button
          type="button"
          onClick={onRefresh}
          className="inline-flex items-center gap-2 rounded-md border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-ink-800 hover:bg-slate-50"
        >
          <RefreshCw className="h-4 w-4" />
          Refresh
        </button>
      </div>
    </div>
  );
}

function SummaryStrip({ counts }) {
  return (
    <div className="grid gap-3 sm:grid-cols-3">
      <SummaryCard label="Total postings" value={counts.total} />
      <SummaryCard label="New" value={counts.new} />
      <SummaryCard label="Applied" value={counts.applied} />
    </div>
  );
}

function SummaryCard({ label, value }) {
  return (
    <div className="rounded-md border border-slate-200 bg-white p-4 shadow-soft">
      <p className="text-sm font-medium text-ink-600">{label}</p>
      <p className="mt-1 text-2xl font-semibold">{value}</p>
    </div>
  );
}

function SegmentedControl({ value, onChange }) {
  return (
    <div className="flex rounded-md border border-slate-200 bg-slate-50 p-1">
      {["all", "new", "applied"].map((item) => (
        <button
          key={item}
          type="button"
          onClick={() => onChange(item)}
          className={`rounded px-3 py-1.5 text-sm font-medium capitalize ${
            value === item ? "bg-white text-ink-950 shadow-sm" : "text-ink-600 hover:text-ink-950"
          }`}
        >
          {item}
        </button>
      ))}
    </div>
  );
}

function SearchBox({ value, onChange, placeholder }) {
  return (
    <label className="relative block w-full md:max-w-sm">
      <Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-ink-400" />
      <input
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        className="w-full rounded-md border border-slate-200 bg-white py-2 pl-9 pr-3 text-sm outline-none ring-blue-100 transition focus:border-blue-400 focus:ring-4"
      />
    </label>
  );
}

function PostingsTable({ postings, onApply }) {
  return (
    <div className="overflow-hidden rounded-md border border-slate-200 bg-white shadow-soft">
      <table className="hidden w-full border-collapse text-sm md:table">
        <thead className="bg-slate-50 text-left text-xs uppercase text-ink-600">
          <tr>
            <th className="px-4 py-3">Company</th>
            <th className="px-4 py-3">Role</th>
            <th className="px-4 py-3">Source</th>
            <th className="px-4 py-3">Date Found</th>
            <th className="px-4 py-3">Apply</th>
            <th className="px-4 py-3">Applied</th>
          </tr>
        </thead>
        <tbody>
          {postings.map((posting) => (
            <tr key={posting.id} className={`border-t border-slate-100 ${posting.applied ? "bg-slate-50 text-ink-400" : ""}`}>
              <td className="px-4 py-3 font-medium">{posting.company}</td>
              <td className={`px-4 py-3 ${posting.applied ? "line-through" : ""}`}>{posting.role}</td>
              <td className="px-4 py-3"><SourceBadge source={posting.source} /></td>
              <td className="px-4 py-3">{formatDate(posting.date_found)}</td>
              <td className="px-4 py-3"><ApplyLink action={posting.apply_action} /></td>
              <td className="px-4 py-3"><AppliedToggle posting={posting} onApply={onApply} /></td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="divide-y divide-slate-100 md:hidden">
        {postings.map((posting) => (
          <div key={posting.id} className={`space-y-3 p-4 ${posting.applied ? "bg-slate-50 text-ink-400" : ""}`}>
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="font-medium">{posting.company}</p>
                <p className={`text-sm ${posting.applied ? "line-through" : "text-ink-800"}`}>{posting.role}</p>
              </div>
              <SourceBadge source={posting.source} />
            </div>
            <div className="flex items-center justify-between gap-3">
              <span className="text-xs text-ink-600">{formatDate(posting.date_found)}</span>
              <div className="flex items-center gap-2">
                <ApplyLink action={posting.apply_action} />
                <AppliedToggle posting={posting} onApply={onApply} />
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function ContactsTable({ contacts }) {
  return (
    <div className="overflow-hidden rounded-md border border-slate-200 bg-white shadow-soft">
      <table className="hidden w-full border-collapse text-sm md:table">
        <thead className="bg-slate-50 text-left text-xs uppercase text-ink-600">
          <tr>
            <th className="px-4 py-3">Company</th>
            <th className="px-4 py-3">Email</th>
            <th className="px-4 py-3">Source Page</th>
            <th className="px-4 py-3">Date Scraped</th>
          </tr>
        </thead>
        <tbody>
          {contacts.map((contact) => (
            <tr key={`${contact.company}-${contact.email}`} className="border-t border-slate-100">
              <td className="px-4 py-3 font-medium">{contact.company}</td>
              <td className="px-4 py-3">{contact.email}</td>
              <td className="px-4 py-3">
                <a className="text-blue-700 hover:underline" href={contact.source_page} target="_blank" rel="noreferrer">
                  Source
                </a>
              </td>
              <td className="px-4 py-3">{formatDate(contact.date_scraped)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="divide-y divide-slate-100 md:hidden">
        {contacts.map((contact) => (
          <div key={`${contact.company}-${contact.email}`} className="space-y-2 p-4">
            <p className="font-medium">{contact.company}</p>
            <p className="text-sm">{contact.email}</p>
            <div className="flex items-center justify-between">
              <a className="text-sm text-blue-700 hover:underline" href={contact.source_page} target="_blank" rel="noreferrer">
                Source page
              </a>
              <span className="text-xs text-ink-600">{formatDate(contact.date_scraped)}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function HealthTable({ companies, flagged }) {
  return (
    <div className="overflow-hidden rounded-md border border-slate-200 bg-white shadow-soft">
      <table className="w-full border-collapse text-sm">
        <thead className="bg-slate-50 text-left text-xs uppercase text-ink-600">
          <tr>
            <th className="px-4 py-3">Company</th>
            <th className="px-4 py-3">Recent Posting Count Trend</th>
            <th className="px-4 py-3">Flag</th>
          </tr>
        </thead>
        <tbody>
          {companies.length === 0 && (
            <tr>
              <td className="px-4 py-4 text-ink-600" colSpan="3">No health trend data yet.</td>
            </tr>
          )}
          {companies.map(([company, counts]) => (
            <tr key={company} className="border-t border-slate-100">
              <td className="px-4 py-3 font-medium">{company}</td>
              <td className="px-4 py-3">{Array.isArray(counts) ? counts.join(" -> ") : counts}</td>
              <td className="px-4 py-3">
                {flagged.has(company) ? (
                  <span className="inline-flex items-center gap-1 text-red-700">
                    <AlertTriangle className="h-4 w-4" />
                    Flagged
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1 text-green-700">
                    <Check className="h-4 w-4" />
                    OK
                  </span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function SourceBadge({ source }) {
  const label = sourceLabel(source);
  const className = sourceClasses[source] || "bg-slate-100 text-slate-700 ring-slate-200";
  return <span className={`inline-flex rounded px-2 py-1 text-xs font-medium ring-1 ${className}`}>{label}</span>;
}

function ApplyLink({ action }) {
  const isEmail = action?.startsWith("mailto:");
  const Icon = isEmail ? Mail : ExternalLink;
  return (
    <a
      href={action}
      target={isEmail ? undefined : "_blank"}
      rel={isEmail ? undefined : "noreferrer"}
      className="inline-flex items-center gap-1.5 rounded-md border border-slate-200 bg-white px-2.5 py-1.5 text-sm font-medium text-ink-800 hover:bg-slate-50"
    >
      <Icon className="h-4 w-4" />
      {isEmail ? "Email" : "Apply"}
    </a>
  );
}

function AppliedToggle({ posting, onApply }) {
  return (
    <button
      type="button"
      disabled={Boolean(posting.applied)}
      onClick={() => onApply(posting.id)}
      className={`inline-flex h-8 w-8 items-center justify-center rounded-md border ${
        posting.applied
          ? "border-green-200 bg-green-50 text-green-700"
          : "border-slate-200 bg-white text-ink-600 hover:bg-slate-50"
      }`}
      aria-label={posting.applied ? "Applied" : "Mark applied"}
      title={posting.applied ? "Applied" : "Mark applied"}
    >
      <Check className="h-4 w-4" />
    </button>
  );
}

function SkeletonRows() {
  return (
    <div className="space-y-2 rounded-md border border-slate-200 bg-white p-4 shadow-soft">
      {[0, 1, 2, 3].map((item) => (
        <div key={item} className="h-12 animate-pulse rounded bg-slate-100" />
      ))}
    </div>
  );
}

function InlineError({ message }) {
  return (
    <div className="rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-800">
      {message}
    </div>
  );
}

function EmptyState({ title, message }) {
  return (
    <div className="rounded-md border border-dashed border-slate-300 bg-white p-8 text-center shadow-soft">
      <Clock className="mx-auto h-8 w-8 text-ink-400" />
      <p className="mt-3 font-medium">{title}</p>
      <p className="mt-1 text-sm text-ink-600">{message}</p>
    </div>
  );
}

function useApi(path, onBackendStatus) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function load() {
    setLoading(true);
    setError("");
    try {
      const response = await apiFetch(path);
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const json = await response.json();
      setData(json);
      onBackendStatus(false);
    } catch (err) {
      setError(`Could not load ${path}: ${err.message}`);
      onBackendStatus(true);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, [path]);

  return { data, setData, loading, error, refetch: load };
}

function healthStatus(value) {
  if (!value) return { level: "red", dot: "bg-red-500" };
  const hours = (Date.now() - new Date(value).getTime()) / 36e5;
  if (hours <= 12) return { level: "green", dot: "bg-green-500" };
  if (hours <= 24) return { level: "yellow", dot: "bg-yellow-400" };
  return { level: "red", dot: "bg-red-500" };
}

function sourceLabel(source) {
  if (source === "career_page") return "Career page";
  if (source === "linkedin") return "LinkedIn";
  if (source === "facebook") return "Facebook";
  return source || "Unknown";
}

function formatDate(value) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}

function csvEscape(value) {
  const text = String(value ?? "");
  if (/[",\n]/.test(text)) return `"${text.replaceAll('"', '""')}"`;
  return text;
}

createRoot(document.getElementById("root")).render(<App />);
