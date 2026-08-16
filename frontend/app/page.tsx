"use client";

import { FormEvent, useEffect, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type Device = {
  id: string;
  hostname: string;
  username: string | null;
  os_name: string | null;
  os_version: string | null;
  agent_version: string | null;
  last_seen_at: string | null;
  online: boolean;
  gateway_latency_ms: number | null;
  internet_latency_ms: number | null;
  packet_loss_pct: number | null;
  interfaces: {
    id: string;
    name: string;
    mac_address: string | null;
    ipv4_address: string | null;
    gateway: string | null;
    dns_servers: string[];
    is_primary: boolean;
  }[];
};

type User = {
  id: string;
  organization_id: string;
  email: string;
  full_name: string;
  role: string;
};

export default function Home() {
  const [mode, setMode] = useState<"login" | "register">("register");
  const [user, setUser] = useState<User | null>(null);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const [devices, setDevices] = useState<Device[]>([]);
  const [devicesLoading, setDevicesLoading] = useState(false);

  const [organizationName, setOrganizationName] = useState("");
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  async function loadDevices() {
    const token = localStorage.getItem("netopsai_token");
    if (!token) return;
    setDevicesLoading(true);
    try {
      const response = await fetch(`${API}/api/v1/devices`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (response.ok) setDevices(await response.json());
    } finally {
      setDevicesLoading(false);
    }
  }

  useEffect(() => {
    const token = localStorage.getItem("netopsai_token");
    if (!token) return;

    fetch(`${API}/api/v1/auth/me`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then(async (res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (data) {
          setUser(data);
          void loadDevices();
        } else {
          localStorage.removeItem("netopsai_token");
        }
      })
      .catch(() => localStorage.removeItem("netopsai_token"));
  }, []);

  useEffect(() => {
    if (!user) return;
    const interval = setInterval(() => void loadDevices(), 15000);
    return () => clearInterval(interval);
  }, [user]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setMessage("");

    const isRegister = mode === "register";
    const endpoint = isRegister
      ? "/api/v1/auth/register"
      : "/api/v1/auth/login";

    const body = isRegister
      ? {
          organization_name: organizationName,
          full_name: fullName,
          email,
          password,
        }
      : { email, password };

    try {
      const response = await fetch(`${API}${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail ?? "Authentication failed");
      }

      localStorage.setItem("netopsai_token", data.access_token);
      setUser(data.user);
      setMessage(isRegister ? "Workspace created successfully." : "Login successful.");
    } catch (error) {
      setMessage(
        error instanceof Error ? error.message : "Something went wrong."
      );
    } finally {
      setLoading(false);
    }
  }

  function logout() {
    localStorage.removeItem("netopsai_token");
    setUser(null);
    setMessage("");
  }

  if (user) {
    return (
      <main>
        <header className="topbar">
          <div>
            <div className="eyebrow">NETOPSAI · ADMIN CONSOLE</div>
            <h1>Network Operations</h1>
            <p>Your organization workspace is authenticated and ready.</p>
          </div>
          <button className="ghost" onClick={logout}>
            Log out
          </button>
        </header>

        <section className="hero">
          <div>
            <div className="eyebrow">SESSION ACTIVE</div>
            <h2>Welcome, {user.full_name}.</h2>
            <p>
              We now have the tenant boundary and authenticated administrator
              session that the monitoring system will use for devices, employees,
              incidents and remediation.
            </p>
          </div>
        </section>

        <section className="grid">
          <article className="card">
            <span>Role</span>
            <strong>{user.role}</strong>
          </article>
          <article className="card">
            <span>Email</span>
            <strong className="small">{user.email}</strong>
          </article>
          <article className="card">
            <span>Organization</span>
            <strong className="small">{user.organization_id}</strong>
          </article>
          <article className="card">
            <span>Session</span>
            <strong>ACTIVE</strong>
          </article>
        </section>

        <section className="panel">
          <div className="eyebrow">DEVICE MONITORING</div>
          <h3>Endpoint health</h3>
          <p>{devicesLoading ? "Loading devices..." : `${devices.length} device${devices.length === 1 ? "" : "s"} registered.`}</p>
          <div style={{ overflowX: "auto", marginTop: 18 }}>
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr>
                  <th style={{ textAlign: "left", padding: "10px 8px" }}>Device</th>
                  <th style={{ textAlign: "left", padding: "10px 8px" }}>Status</th>
                  <th style={{ textAlign: "left", padding: "10px 8px" }}>IP</th>
                  <th style={{ textAlign: "left", padding: "10px 8px" }}>MAC</th>
                  <th style={{ textAlign: "left", padding: "10px 8px" }}>Latency</th>
                  <th style={{ textAlign: "left", padding: "10px 8px" }}>Loss</th>
                </tr>
              </thead>
              <tbody>
                {devices.map((device) => {
                  const primary = device.interfaces.find((item) => item.is_primary) ?? device.interfaces[0];
                  return (
                    <tr key={device.id}>
                      <td style={{ padding: "10px 8px" }}>{device.hostname}</td>
                      <td style={{ padding: "10px 8px" }}>{device.online ? "ONLINE" : "OFFLINE"}</td>
                      <td style={{ padding: "10px 8px" }}>{primary?.ipv4_address ?? "--"}</td>
                      <td style={{ padding: "10px 8px" }}>{primary?.mac_address ?? "--"}</td>
                      <td style={{ padding: "10px 8px" }}>{device.internet_latency_ms == null ? "--" : `${device.internet_latency_ms} ms`}</td>
                      <td style={{ padding: "10px 8px" }}>{device.packet_loss_pct == null ? "--" : `${device.packet_loss_pct}%`}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </section>

        <section className="panel">
          <div className="eyebrow">NEXT MILESTONE</div>
          <h3>Endpoint Monitoring</h3>
          <p>
            Next we register the first Windows/Linux agent and collect hostname,
            IP, MAC, gateway, DNS, latency and packet-loss data.
          </p>
        </section>
      </main>
    );
  }

  return (
    <main>
      <header className="topbar">
        <div>
          <div className="eyebrow">DAY 1 · SAAS FOUNDATION</div>
          <h1>NetOpsAI</h1>
          <p>AI-powered Network Operations Platform</p>
        </div>
        <div className="status">AUTHENTICATION</div>
      </header>

      <section className="auth-shell">
        <section className="auth-copy">
          <div className="eyebrow">OBSERVE · DIAGNOSE · SIMULATE · ACT</div>
          <h2>Build your network operations workspace.</h2>
          <p>
            Create the first organization and administrator account. This
            organization becomes the tenant boundary for every device, employee,
            incident and remediation action.
          </p>

          <div className="feature-list">
            <div>✓ Multi-tenant organization</div>
            <div>✓ Secure password hashing</div>
            <div>✓ JWT authentication</div>
            <div>✓ Protected admin session</div>
          </div>
        </section>

        <section className="auth-card">
          <div className="tabs">
            <button
              type="button"
              className={mode === "register" ? "active" : ""}
              onClick={() => {
                setMode("register");
                setMessage("");
              }}
            >
              Create workspace
            </button>
            <button
              type="button"
              className={mode === "login" ? "active" : ""}
              onClick={() => {
                setMode("login");
                setMessage("");
              }}
            >
              Log in
            </button>
          </div>

          <form onSubmit={submit}>
            {mode === "register" && (
              <>
                <label>
                  Organization name
                  <input
                    value={organizationName}
                    onChange={(e) => setOrganizationName(e.target.value)}
                    required
                    placeholder="Acme Technologies"
                  />
                </label>

                <label>
                  Your name
                  <input
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    required
                    placeholder="Rahul Jangra"
                  />
                </label>
              </>
            )}

            <label>
              Email
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                placeholder="admin@example.com"
              />
            </label>

            <label>
              Password
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={8}
                placeholder="Minimum 8 characters"
              />
            </label>

            <button className="primary" disabled={loading}>
              {loading
                ? "Working..."
                : mode === "register"
                  ? "Create organization"
                  : "Log in"}
            </button>
          </form>

          {message && <div className="message">{message}</div>}
        </section>
      </section>
    </main>
  );
}
