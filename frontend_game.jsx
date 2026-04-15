// src/App.jsx
import React from "react";
import { createRoot } from "react-dom/client";
import {
  BrowserRouter,
  Routes,
  Route,
  Link,
  Navigate,
  withRouter,
  useNavigate,
} from "react-router-dom";
import axios from "axios";
import { jwtDecode } from "jwt-decode";
import "./index.css"; // تأكد أن Tailwind مُفعّل هنا

/* ============================
   إعداد Axios
   ============================ */
const API_BASE = import.meta.env.VITE_API_BASE || "http://127.0.0.1:8000";
const api = axios.create({
  baseURL: API_BASE,
  timeout: 10000,
  headers: { "Content-Type": "application/json" },
});

/* ============================
   AuthContext (React Context)
   - سنوفر AuthProvider كـ Class Component
   - يخزن token و user، يضيف interceptor للـ axios
   - يدير auto-logout بناءً على exp في التوكن
   ============================ */
const AuthContext = React.createContext();

class AuthProvider extends React.Component {
  constructor(props) {
    super(props);
    const token = localStorage.getItem("khufu_token");
    const userRaw = localStorage.getItem("khufu_user");
    this.state = {
      token: token || null,
      user: userRaw ? JSON.parse(userRaw) : null,
      loading: false,
    };
    this.logoutTimer = null;
    this.requestInterceptor = null;
    this.responseInterceptor = null;
  }

  componentDidMount() {
    // attach interceptors
    this.requestInterceptor = api.interceptors.request.use((cfg) => {
      if (this.state.token) cfg.headers.Authorization = `Bearer ${this.state.token}`;
      return cfg;
    });

    this.responseInterceptor = api.interceptors.response.use(
      (res) => res,
      (err) => {
        const status = err?.response?.status;
        if (status === 401 || status === 403) {
          this.logout();
        }
        return Promise.reject(err);
      }
    );

    // schedule auto logout if token exists
    if (this.state.token) this.scheduleAutoLogout(this.state.token);
  }

  componentWillUnmount() {
    if (this.requestInterceptor) api.interceptors.request.eject(this.requestInterceptor);
    if (this.responseInterceptor) api.interceptors.response.eject(this.responseInterceptor);
    if (this.logoutTimer) clearTimeout(this.logoutTimer);
  }

  scheduleAutoLogout = (token) => {
    try {
      const { exp } = jwtDecode(token);
      const msLeft = exp * 1000 - Date.now();
      if (msLeft <= 0) {
        this.logout();
        return;
      }
      if (this.logoutTimer) clearTimeout(this.logoutTimer);
      this.logoutTimer = setTimeout(() => this.logout(), msLeft);
    } catch (e) {
      this.logout();
    }
  };

  login = async ({ username, password }) => {
    this.setState({ loading: true });
    try {
      const res = await api.post("/auth/login", { username, password });
      const token = res.data.access_token;
      localStorage.setItem("khufu_token", token);
      this.setState({ token });
      // fetch profile
      const profile = await this.fetchProfile(username, token);
      this.setState({ user: profile });
      localStorage.setItem("khufu_user", JSON.stringify(profile));
      this.scheduleAutoLogout(token);
      return { ok: true };
    } catch (err) {
      return { ok: false, error: err?.response?.data?.detail || err.message };
    } finally {
      this.setState({ loading: false });
    }
  };

  register = async ({ username, password }) => {
    this.setState({ loading: true });
    try {
      const res = await api.post("/auth/register", { username, password });
      const token = res.data.access_token;
      localStorage.setItem("khufu_token", token);
      this.setState({ token });
      const profile = await this.fetchProfile(username, token);
      this.setState({ user: profile });
      localStorage.setItem("khufu_user", JSON.stringify(profile));
      this.scheduleAutoLogout(token);
      return { ok: true };
    } catch (err) {
      return { ok: false, error: err?.response?.data?.detail || err.message };
    } finally {
      this.setState({ loading: false });
    }
  };

  fetchProfile = async (username, overrideToken) => {
    try {
      const cfg = overrideToken ? { headers: { Authorization: `Bearer ${overrideToken}` } } : {};
      const res = await api.get(`/players/${username}`, cfg);
      return res.data;
    } catch (e) {
      return null;
    }
  };

  logout = () => {
    localStorage.removeItem("khufu_token");
    localStorage.removeItem("khufu_user");
    this.setState({ token: null, user: null });
    if (this.logoutTimer) {
      clearTimeout(this.logoutTimer);
      this.logoutTimer = null;
    }
    // redirect to login if router available
    if (window.location.pathname !== "/login") window.location.href = "/login";
  };

  refreshProfile = async () => {
    if (!this.state.user?.username) return;
    try {
      const res = await api.get(`/players/${this.state.user.username}`);
      this.setState({ user: res.data });
      localStorage.setItem("khufu_user", JSON.stringify(res.data));
    } catch (e) {
      // ignore
    }
  };

  render() {
    const ctx = {
      token: this.state.token,
      user: this.state.user,
      loading: this.state.loading,
      login: this.login,
      register: this.register,
      logout: this.logout,
      refreshProfile: this.refreshProfile,
      setUser: (u) => {
        this.setState({ user: u });
        localStorage.setItem("khufu_user", JSON.stringify(u));
      },
    };
    return <AuthContext.Provider value={ctx}>{this.props.children}</AuthContext.Provider>;
  }
}

/* Helper hook for class components to access context */
function withAuth(Component) {
  return function Wrapped(props) {
    return (
      <AuthContext.Consumer>
        {(ctx) => <Component {...props} auth={ctx} />}
      </AuthContext.Consumer>
    );
  };
}

/* ============================
   UI Utilities (simple toast)
   ============================ */
class Toast extends React.Component {
  state = { messages: [] };

  add = (msg, type = "info") => {
    const id = Date.now() + Math.random();
    this.setState((s) => ({ messages: [...s.messages, { id, msg, type }] }));
    setTimeout(() => this.remove(id), 4500);
  };

  remove = (id) => {
    this.setState((s) => ({ messages: s.messages.filter((m) => m.id !== id) }));
  };

  render() {
    return (
      <div className="fixed right-4 top-4 z-50 space-y-2">
        {this.state.messages.map((m) => (
          <div
            key={m.id}
            className={`px-4 py-2 rounded shadow-lg text-sm ${
              m.type === "error" ? "bg-red-600" : "bg-amber-500 text-black"
            }`}
          >
            {m.msg}
          </div>
        ))}
      </div>
    );
  }
}
const toastRef = React.createRef();

/* ============================
   Topbar (class)
   ============================ */
class TopbarBase extends React.Component {
  render() {
    const { auth } = this.props;
    return (
      <header className="bg-[#07070a] border-b border-[#1f1f23]">
        <div className="container mx-auto px-4 py-3 flex items-center justify-between">
          <Link to="/" className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-full bg-gradient-to-br from-yellow-400 to-amber-600 flex items-center justify-center text-black font-bold">
              K
            </div>
            <div>
              <div className="text-lg font-bold">King Khufu Adventure</div>
              <div className="text-xs text-slate-400">Ancient Egypt meets modern gaming</div>
            </div>
          </Link>

          <nav className="flex items-center space-x-4">
            <Link to="/leaderboard" className="text-slate-300 hover:text-white">Leaderboard</Link>
            <Link to="/market" className="text-slate-300 hover:text-white">Market</Link>
            <Link to="/auctions" className="text-slate-300 hover:text-white">Auctions</Link>
            <Link to="/shop" className="text-slate-300 hover:text-white">Shop</Link>

            {auth.user ? (
              <div className="flex items-center space-x-3">
                <div className="text-sm text-slate-300">Hi, {auth.user.username}</div>
                <button
                  onClick={() => auth.logout()}
                  className="px-3 py-1 rounded bg-[#1f2937] hover:bg-[#111214] text-sm"
                >
                  Logout
                </button>
              </div>
            ) : (
              <div className="flex items-center space-x-2">
                <Link to="/login" className="px-3 py-1 rounded bg-[#1f2937] hover:bg-[#111214] text-sm">Login</Link>
                <Link to="/register" className="px-3 py-1 rounded bg-amber-500 text-black text-sm">Register</Link>
              </div>
            )}
          </nav>
        </div>
      </header>
    );
  }
}
const Topbar = withAuth(TopbarBase);

/* ============================
   Leaderboard (Class) - WebSocket
   ============================ */
class Leaderboard extends React.Component {
  constructor(props) {
    super(props);
    this.state = { players: [], changed: {} };
    this.ws = null;
    this.backoff = 1000;
    this.mounted = false;
  }

  componentDidMount() {
    this.mounted = true;
    this.connect();
    this.fetchInitial();
  }

  componentWillUnmount() {
    this.mounted = false;
    if (this.ws) this.ws.close();
  }

  fetchInitial = async () => {
    try {
      const res = await api.get("/leaderboard");
      const list = res.data.top_players || res.data || [];
      this.applyUpdate(list.slice(0, 10));
    } catch (e) {
      // ignore
    }
  };

  applyUpdate = (newList) => {
    const oldIndex = {};
    this.state.players.forEach((p, i) => (oldIndex[p.username] = i));
    const changed = {};
    newList.forEach((p, i) => {
      const prev = oldIndex[p.username];
      if (prev === undefined) changed[p.username] = true;
      else if (prev !== i) changed[p.username] = true;
    });
    this.setState({ players: newList, changed });
    setTimeout(() => {
      if (this.mounted) this.setState({ changed: {} });
    }, 900);
  };

  connect = () => {
    const base = API_BASE;
    const wsUrl = (base.replace(/^http/, "ws") + "/ws/leaderboard").replace("http://", "ws://").replace("https://", "wss://");
    try {
      this.ws = new WebSocket(wsUrl);
      this.ws.onopen = () => {
        this.backoff = 1000;
        // console.log("WS connected");
      };
      this.ws.onmessage = (evt) => {
        try {
          const msg = JSON.parse(evt.data);
          if (msg.type === "leaderboard_init" || msg.type === "leaderboard_update") {
            const list = msg.data.slice(0, 10);
            this.applyUpdate(list);
          }
        } catch (e) {}
      };
      this.ws.onclose = () => {
        if (!this.mounted) return;
        this.reconnect();
      };
      this.ws.onerror = () => {
        if (this.ws) this.ws.close();
      };
    } catch (e) {
      this.reconnect();
    }
  };

  reconnect = () => {
    const delay = this.backoff;
    this.backoff = Math.min(this.backoff * 1.8, 30000);
    setTimeout(() => {
      if (this.mounted) this.connect();
    }, delay);
  };

  render() {
    return (
      <section className="max-w-3xl mx-auto">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-2xl font-extrabold tracking-tight">Leaderboard</h2>
          <div className="text-sm text-slate-400">Real-time top players</div>
        </div>

        <div className="space-y-3">
          {this.state.players.length === 0 ? (
            <div className="p-6 bg-[#0f0f12] rounded-md text-center text-slate-400">No data yet</div>
          ) : (
            this.state.players.map((p, idx) => (
              <div key={p.username} className={`flex items-center justify-between px-4 py-2 rounded-md transition-transform duration-500 ${this.state.changed[p.username] ? "transform scale-105 bg-gradient-to-r from-[#2b2b2f] to-[#1a1a1d] shadow-lg" : "bg-[#0f0f12]"}`}>
                <div className="flex items-center space-x-3">
                  <div className="w-10 h-10 rounded-full bg-gradient-to-br from-yellow-400 to-amber-600 flex items-center justify-center text-black font-bold">
                    {idx + 1}
                  </div>
                  <div>
                    <div className="font-semibold">{p.username}</div>
                    <div className="text-xs text-slate-400">Level {p.level}</div>
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-lg font-bold text-yellow-300">{p.coins} ✦</div>
                </div>
              </div>
            ))
          )}
        </div>
      </section>
    );
  }
}

/* ============================
   Login Page (Class)
   ============================ */
class LoginPageBase extends React.Component {
  state = { username: "", password: "", loading: false, error: null };

  onSubmit = async (e) => {
    e.preventDefault();
    const { username, password } = this.state;
    this.setState({ loading: true, error: null });
    const res = await this.props.auth.login({ username, password });
    this.setState({ loading: false });
    if (!res.ok) {
      this.setState({ error: res.error || "Login failed" });
      if (toastRef.current) toastRef.current.add(res.error || "Login failed", "error");
    } else {
      if (toastRef.current) toastRef.current.add("Logged in", "info");
      window.location.href = "/dashboard";
    }
  };

  render() {
    return (
      <div className="max-w-md mx-auto bg-[#0b0b0f] p-6 rounded shadow">
        <h3 className="text-xl font-bold mb-4">Login</h3>
        <form onSubmit={this.onSubmit} className="space-y-3">
          <input value={this.state.username} onChange={(e) => this.setState({ username: e.target.value })} placeholder="Username" className="w-full p-2 rounded bg-[#0f1720] border border-[#1f2937]" />
          <input value={this.state.password} onChange={(e) => this.setState({ password: e.target.value })} placeholder="Password" type="password" className="w-full p-2 rounded bg-[#0f1720] border border-[#1f2937]" />
          {this.state.error && <div className="text-red-400 text-sm">{this.state.error}</div>}
          <div className="flex items-center justify-between">
            <button type="submit" disabled={this.state.loading} className="px-4 py-2 bg-amber-500 text-black rounded">
              {this.state.loading ? "Signing..." : "Sign in"}
            </button>
            <Link to="/register" className="text-sm text-slate-400">Create account</Link>
          </div>
        </form>
      </div>
    );
  }
}
const LoginPage = withAuth(LoginPageBase);

/* ============================
   Register Page (Class)
   ============================ */
class RegisterPageBase extends React.Component {
  state = { username: "", password: "", loading: false, error: null };

  onSubmit = async (e) => {
    e.preventDefault();
    const { username, password } = this.state;
    this.setState({ loading: true, error: null });
    const res = await this.props.auth.register({ username, password });
    this.setState({ loading: false });
    if (!res.ok) {
      this.setState({ error: res.error || "Register failed" });
      if (toastRef.current) toastRef.current.add(res.error || "Register failed", "error");
    } else {
      if (toastRef.current) toastRef.current.add("Registered and logged in", "info");
      window.location.href = "/dashboard";
    }
  };

  render() {
    return (
      <div className="max-w-md mx-auto bg-[#0b0b0f] p-6 rounded shadow">
        <h3 className="text-xl font-bold mb-4">Register</h3>
        <form onSubmit={this.onSubmit} className="space-y-3">
          <input value={this.state.username} onChange={(e) => this.setState({ username: e.target.value })} placeholder="Username" className="w-full p-2 rounded bg-[#0f1720] border border-[#1f2937]" />
          <input value={this.state.password} onChange={(e) => this.setState({ password: e.target.value })} placeholder="Password" type="password" className="w-full p-2 rounded bg-[#0f1720] border border-[#1f2937]" />
          {this.state.error && <div className="text-red-400 text-sm">{this.state.error}</div>}
          <div className="flex items-center justify-between">
            <button type="submit" disabled={this.state.loading} className="px-4 py-2 bg-amber-500 text-black rounded">
              {this.state.loading ? "Creating..." : "Create account"}
            </button>
            <Link to="/login" className="text-sm text-slate-400">Already have an account?</Link>
          </div>
        </form>
      </div>
    );
  }
}
const RegisterPage = withAuth(RegisterPageBase);

/* ============================
   Dashboard (Class)
   - shows profile, achievements, notifications, daily challenge
   ============================ */
class DashboardBase extends React.Component {
  state = { profile: null, achievements: [], notifications: [], daily: null, loading: true };

  async componentDidMount() {
    const { auth } = this.props;
    if (!auth.user) {
      // redirect handled by route protection
      this.setState({ loading: false });
      return;
    }
    await this.loadAll();
  }

  loadAll = async () => {
    const { auth } = this.props;
    this.setState({ loading: true });
    try {
      const username = auth.user.username;
      const [profileRes, achRes, notRes, dailyRes] = await Promise.allSettled([
        api.get(`/players/${username}`),
        api.get(`/achievements/${username}`),
        api.get(`/notifications/${username}`),
        api.get("/daily_challenge"),
      ]);
      if (profileRes.status === "fulfilled") {
        this.setState({ profile: profileRes.value.data });
        auth.setUser(profileRes.value.data);
      }
      if (achRes.status === "fulfilled") this.setState({ achievements: achRes.value.data.achievements || [] });
      if (notRes.status === "fulfilled") this.setState({ notifications: notRes.value.data.notifications || [] });
      if (dailyRes.status === "fulfilled") this.setState({ daily: dailyRes.value.data.challenge });
    } catch (e) {
      // ignore
    } finally {
      this.setState({ loading: false });
    }
  };

  render() {
    const { profile, achievements, notifications, daily, loading } = this.state;
    if (loading) return <div className="p-6">Loading...</div>;
    return (
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="md:col-span-2 space-y-4">
          <div className="bg-[#0f0f12] p-4 rounded">
            <div className="flex items-center space-x-4">
              <div className="w-20 h-20 rounded-full bg-[#1f2937] flex items-center justify-center text-2xl font-bold text-amber-400">
                {profile?.username?.charAt(0)?.toUpperCase() || "P"}
              </div>
              <div>
                <div className="text-xl font-bold">{profile?.username}</div>
                <div className="text-sm text-slate-400">Level {profile?.level} • {profile?.coins} ✦</div>
                <div className="mt-2 text-sm">Avatar: {profile?.avatar} • Outfit: {profile?.outfit}</div>
              </div>
            </div>
          </div>

          <div className="bg-[#0f0f12] p-4 rounded">
            <h4 className="font-bold mb-2">Achievements</h4>
            {achievements.length === 0 ? <div className="text-slate-400">No achievements yet</div> : (
              <ul className="list-disc list-inside">
                {achievements.map((a, i) => <li key={i}>{a}</li>)}
              </ul>
            )}
          </div>

          <div className="bg-[#0f0f12] p-4 rounded">
            <h4 className="font-bold mb-2">Notifications</h4>
            {notifications.length === 0 ? <div className="text-slate-400">No notifications</div> : (
              <ul className="space-y-1">
                {notifications.map((n, i) => <li key={i} className="text-sm text-slate-300">{n.message || n}</li>)}
              </ul>
            )}
          </div>
        </div>

        <aside className="space-y-4">
          <div className="bg-[#0f0f12] p-4 rounded">
            <h4 className="font-bold mb-2">Daily Challenge</h4>
            <div className="text-slate-300">{daily || "No challenge today"}</div>
          </div>

          <div className="bg-[#0f0f12] p-4 rounded">
            <h4 className="font-bold mb-2">Quick Actions</h4>
            <div className="flex flex-col space-y-2">
              <Link to="/shop" className="px-3 py-2 bg-amber-500 text-black rounded text-center">Open Shop</Link>
              <Link to="/market" className="px-3 py-2 bg-[#1f2937] rounded text-center">Open Marketplace</Link>
              <Link to="/auctions" className="px-3 py-2 bg-[#1f2937] rounded text-center">Open Auctions</Link>
            </div>
          </div>
        </aside>
      </div>
    );
  }
}
const Dashboard = withAuth(DashboardBase);

/* ============================
   Market Page (Class) - view, sell, buy (pagination)
   ============================ */
class MarketPageBase extends React.Component {
  state = { items: [], skip: 0, limit: 10, loading: false, sellForm: { item: "", price: "" } };

  componentDidMount() {
    this.load();
  }

  load = async () => {
    this.setState({ loading: true });
    try {
      const res = await api.get("/marketplace", { params: { skip: this.state.skip, limit: this.state.limit } });
      this.setState({ items: res.data.items || [] });
    } catch (e) {
      if (toastRef.current) toastRef.current.add("Failed to load marketplace", "error");
    } finally {
      this.setState({ loading: false });
    }
  };

  buy = async (id) => {
    try {
      const buyer = this.props.auth.user?.username;
      const res = await api.post("/marketplace/buy", { buyer, item_id: id });
      if (res.data.status === "success") {
        if (toastRef.current) toastRef.current.add("Item bought", "info");
        this.load();
        this.props.auth.refreshProfile();
      } else {
        if (toastRef.current) toastRef.current.add(res.data.reason || "Failed", "error");
      }
    } catch (e) {
      if (toastRef.current) toastRef.current.add(e?.response?.data?.detail || "Buy failed", "error");
    }
  };

  sell = async (e) => {
    e.preventDefault();
    const seller = this.props.auth.user?.username;
    const { item, price } = this.state.sellForm;
    if (!item || !price) {
      if (toastRef.current) toastRef.current.add("Fill form", "error");
      return;
    }
    try {
      const res = await api.post("/marketplace/sell", { seller, item, price: parseInt(price, 10) });
      if (res.data.status === "success") {
        if (toastRef.current) toastRef.current.add("Item listed", "info");
        this.setState({ sellForm: { item: "", price: "" } });
        this.load();
      }
    } catch (e) {
      if (toastRef.current) toastRef.current.add("Sell failed", "error");
    }
  };

  render() {
    return (
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="md:col-span-2 space-y-4">
          <div className="bg-[#0f0f12] p-4 rounded">
            <h3 className="font-bold mb-3">Marketplace</h3>
            {this.state.loading ? <div>Loading...</div> : (
              <div className="space-y-3">
                {this.state.items.map((it) => (
                  <div key={it.id} className="flex items-center justify-between p-3 bg-[#0b0b0f] rounded">
                    <div>
                      <div className="font-semibold">{it.item}</div>
                      <div className="text-sm text-slate-400">Seller: {it.seller}</div>
                    </div>
                    <div className="flex items-center space-x-3">
                      <div className="text-yellow-300 font-bold">{it.price} ✦</div>
                      <button onClick={() => this.buy(it.id)} className="px-3 py-1 bg-amber-500 text-black rounded">Buy</button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        <aside className="space-y-4">
          <div className="bg-[#0f0f12] p-4 rounded">
            <h4 className="font-bold mb-2">Sell Item</h4>
            <form onSubmit={this.sell} className="space-y-2">
              <input value={this.state.sellForm.item} onChange={(e) => this.setState({ sellForm: { ...this.state.sellForm, item: e.target.value } })} placeholder="Item name" className="w-full p-2 rounded bg-[#0f1720]" />
              <input value={this.state.sellForm.price} onChange={(e) => this.setState({ sellForm: { ...this.state.sellForm, price: e.target.value } })} placeholder="Price" type="number" className="w-full p-2 rounded bg-[#0f1720]" />
              <button type="submit" className="w-full px-3 py-2 bg-amber-500 text-black rounded">List for sale</button>
            </form>
          </div>
        </aside>
      </div>
    );
  }
}
const MarketPage = withAuth(MarketPageBase);

/* ============================
   Auctions Page (Class)
   - create auction, list auctions, place bid (escrow handled by backend)
   ============================ */
class AuctionsPageBase extends React.Component {
  state = { auctions: [], form: { item: "", base_price: "", duration_minutes: 10 }, loading: false };

  componentDidMount() {
    this.load();
  }

  load = async () => {
    this.setState({ loading: true });
    try {
      const res = await api.get("/auctions");
      this.setState({ auctions: res.data.auctions || [] });
    } catch (e) {
      if (toastRef.current) toastRef.current.add("Failed to load auctions", "error");
    } finally {
      this.setState({ loading: false });
    }
  };

  create = async (e) => {
    e.preventDefault();
    const seller = this.props.auth.user?.username;
    const { item, base_price, duration_minutes } = this.state.form;
    if (!item || !base_price) {
      if (toastRef.current) toastRef.current.add("Fill form", "error");
      return;
    }
    try {
      const res = await api.post("/auction/create", { seller, item, base_price: parseInt(base_price, 10), duration_minutes: parseInt(duration_minutes, 10) });
      if (res.data.status === "success") {
        if (toastRef.current) toastRef.current.add("Auction created", "info");
        this.setState({ form: { item: "", base_price: "", duration_minutes: 10 } });
        this.load();
      }
    } catch (e) {
      if (toastRef.current) toastRef.current.add("Create failed", "error");
    }
  };

  bid = async (auctionId, itemName) => {
    const bidder = this.props.auth.user?.username;
    const bid_amount = parseInt(prompt("Enter your bid amount (integer):"), 10);
    if (!bid_amount || isNaN(bid_amount)) return;
    try {
      const res = await api.post("/auction/bid", { bidder, item: itemName, bid_amount });
      if (res.data.status === "success") {
        if (toastRef.current) toastRef.current.add("Bid placed", "info");
        this.load();
        this.props.auth.refreshProfile();
      }
    } catch (e) {
      if (toastRef.current) toastRef.current.add(e?.response?.data?.detail || "Bid failed", "error");
    }
  };

  render() {
    return (
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="md:col-span-2 space-y-4">
          <div className="bg-[#0f0f12] p-4 rounded">
            <h3 className="font-bold mb-3">Active Auctions</h3>
            {this.state.loading ? <div>Loading...</div> : (
              <div className="space-y-3">
                {this.state.auctions.map((a) => (
                  <div key={a.id} className="flex items-center justify-between p-3 bg-[#0b0b0f] rounded">
                    <div>
                      <div className="font-semibold">{a.item}</div>
                      <div className="text-sm text-slate-400">Seller: {a.seller}</div>
                      <div className="text-xs text-slate-400">Ends: {new Date(a.end_time).toLocaleString()}</div>
                    </div>
                    <div className="flex items-center space-x-3">
                      <div className="text-yellow-300 font-bold">{a.highest_bid} ✦</div>
                      <button onClick={() => this.bid(a.id, a.item)} className="px-3 py-1 bg-amber-500 text-black rounded">Place Bid</button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        <aside className="space-y-4">
          <div className="bg-[#0f0f12] p-4 rounded">
            <h4 className="font-bold mb-2">Create Auction</h4>
            <form onSubmit={this.create} className="space-y-2">
              <input value={this.state.form.item} onChange={(e) => this.setState({ form: { ...this.state.form, item: e.target.value } })} placeholder="Item name" className="w-full p-2 rounded bg-[#0f1720]" />
              <input value={this.state.form.base_price} onChange={(e) => this.setState({ form: { ...this.state.form, base_price: e.target.value } })} placeholder="Base price" type="number" className="w-full p-2 rounded bg-[#0f1720]" />
              <input value={this.state.form.duration_minutes} onChange={(e) => this.setState({ form: { ...this.state.form, duration_minutes: e.target.value } })} placeholder="Duration minutes" type="number" className="w-full p-2 rounded bg-[#0f1720]" />
              <button type="submit" className="w-full px-3 py-2 bg-amber-500 text-black rounded">Create</button>
            </form>
          </div>
        </aside>
      </div>
    );
  }
}
const AuctionsPage = withAuth(AuctionsPageBase);

/* ============================
   Shop Page (Class) - fixed items
   ============================ */
class ShopPageBase extends React.Component {
  PRICES = {
    double_jump: 5,
    shield: 7,
    magic: 10,
    strength: 12,
    speed: 15,
    camel: 20,
    fast_mode: 25,
    pharaonic_outfit: 15,
    avatar_warrior: 10,
  };

  buy = async (item) => {
    const username = this.props.auth.user?.username;
    try {
      const res = await api.post("/shop/buy", null, { params: { username, item } });
      if (res.data.status === "success") {
        if (toastRef.current) toastRef.current.add("Purchased " + item, "info");
        this.props.auth.refreshProfile();
      } else {
        if (toastRef.current) toastRef.current.add(res.data.reason || "Failed", "error");
      }
    } catch (e) {
      if (toastRef.current) toastRef.current.add(e?.response?.data?.detail || "Buy failed", "error");
    }
  };

  render() {
    return (
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="md:col-span-3">
          <h3 className="text-xl font-bold mb-4">Official Shop</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {Object.entries(this.PRICES).map(([k, v]) => (
              <div key={k} className="bg-[#0f0f12] p-4 rounded">
                <div className="font-semibold mb-2">{k.replace("_", " ")}</div>
                <div className="text-yellow-300 font-bold mb-3">{v} ✦</div>
                <button onClick={() => this.buy(k)} className="px-3 py-2 bg-amber-500 text-black rounded">Buy</button>
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  }
}
const ShopPage = withAuth(ShopPageBase);

/* ============================
   ProtectedRoute HOC (class-friendly)
   ============================ */
class ProtectedRouteBase extends React.Component {
  render() {
    const { auth, children } = this.props;
    if (auth.loading) return <div className="p-6">Loading...</div>;
    if (!auth.user) return <Navigate to="/login" replace />;
    return children;
  }
}
const ProtectedRoute = withAuth(ProtectedRouteBase);

/* ============================
   App Root (class wrapper for Router)
   ============================ */
class AppRoot extends React.Component {
  render() {
    return (
      <BrowserRouter>
        <AuthProvider>
          <Topbar />
          <main className="container mx-auto px-4 py-6">
            <Routes>
              <Route path="/" element={<Navigate to="/dashboard" replace />} />
              <Route path="/login" element={<LoginPage />} />
              <Route path="/register" element={<RegisterPage />} />

              <Route path="/dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
              <Route path="/leaderboard" element={<ProtectedRoute><Leaderboard /></ProtectedRoute>} />
              <Route path="/market" element={<ProtectedRoute><MarketPage /></ProtectedRoute>} />
              <Route path="/auctions" element={<ProtectedRoute><AuctionsPage /></ProtectedRoute>} />
              <Route path="/shop" element={<ProtectedRoute><ShopPage /></ProtectedRoute>} />

              <Route path="*" element={<div className="text-center py-20">Page not found</div>} />
            </Routes>
          </main>
          <div ref={toastRef} />
          {/* toast instance */}
          <Toast ref={toastRef} />
        </AuthProvider>
      </BrowserRouter>
    );
  }
}

/* ============================
   Mount
   ============================ */
createRoot(document.getElementById("root")).render(<AppRoot />);

/* ============================
   Notes:
   - هذا ملف واحد كامل يعتمد على Tailwind و Vite.
   - استبدل أو أضف تحسينات حسب الحاجة (مثلاً: تحسين UI، إضافة اختبارات).
   - بعض وظائف الـ backend (مثل escrow) مفترضة أنها مُنفذة في السيرفر.
   ============================ */
