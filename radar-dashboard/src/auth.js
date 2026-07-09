import { createClient } from "@supabase/supabase-js";
import { API_BASE_URL } from "./config";

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY;

export const authConfigured = Boolean(supabaseUrl && supabaseAnonKey);
export const supabase = authConfigured
  ? createClient(supabaseUrl, supabaseAnonKey, {
      auth: { persistSession: true, autoRefreshToken: true, detectSessionInUrl: true },
    })
  : null;

export async function apiFetch(path, options = {}) {
  if (!supabase) throw new Error("Supabase authentication is not configured");
  const { data, error } = await supabase.auth.getSession();
  if (error || !data.session) throw new Error("Your session has expired");

  const headers = new Headers(options.headers || {});
  headers.set("Authorization", `Bearer ${data.session.access_token}`);
  if (options.body && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  return fetch(`${API_BASE_URL}${path}`, { ...options, headers });
}

