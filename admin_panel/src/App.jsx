import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  Clock3,
  LogOut,
  RefreshCw,
  Shield,
  Siren,
  Smartphone,
} from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';

import { hasSupabaseConfig, supabase } from './supabaseClient.js';

// Tazelik eşikleri scraper/freshness.py ve database/add_price_verification.sql
// ile AYNI olmalı. Eskiden burası 72 saatti; pg_cron 12 saatte bayat
// işaretlediği için panel "Temiz" derken uygulama aynı fiyata "⚠️ Bayat"
// diyordu (yol haritası S0-4).
const PRICE_STALE_HOURS = 12;
const NEWS_STALE_HOURS = 48;
const ACTIVE_NOW_MINUTES = 15;
const PAGE_SIZE = 1000;
const BRANDS = ['Shell', 'TotalEnergies', 'Türkiye Petrolleri', 'Opet', 'Petrol Ofisi', 'BP', 'Aytemiz'];

function ageHours(value) {
  if (!value) return null;
  const time = new Date(value).getTime();
  if (Number.isNaN(time)) return null;
  return Math.max(0, (Date.now() - time) / 36e5);
}

function ageLabel(value) {
  const hours = ageHours(value);
  if (hours === null) return '-';
  if (hours < 1) return '<1s';
  if (hours < 24) return `${Math.floor(hours)}s`;
  return `${Math.floor(hours / 24)}g`;
}

function isAfter(value, cutoffMs) {
  const time = new Date(value || 0).getTime();
  return !Number.isNaN(time) && time >= cutoffMs;
}

function clearAuthErrorHash() {
  if (!window.location.hash.includes('error=')) return;
  const cleanUrl = new URL(import.meta.env.BASE_URL, window.location.origin).toString();
  window.history.replaceState({}, document.title, cleanUrl);
}

async function fetchAllRows(createQuery, pageSize = PAGE_SIZE) {
  const rows = [];

  for (let from = 0; ; from += pageSize) {
    const to = from + pageSize - 1;
    const result = await createQuery().range(from, to);
    if (result.error) return { data: rows, error: result.error };

    const page = result.data || [];
    rows.push(...page);
    if (page.length < pageSize) break;
  }

  return { data: rows, error: null };
}

function normalizeStationRows(rows) {
  return rows.reduce((acc, row) => {
    const brand = row.marka || 'Bilinmeyen';
    if (!acc[brand]) {
      acc[brand] = { total: 0, active: 0, visible: 0, cities: new Set() };
    }
    acc[brand].total += 1;
    if (row.aktif === true) acc[brand].active += 1;
    if (row.visibility_status === 'visible') acc[brand].visible += 1;
    if (row.il) acc[brand].cities.add(row.il);
    return acc;
  }, {});
}

function normalizePriceRows(priceRows, stationRows) {
  const stationBrand = new Map(stationRows.map((row) => [row.id, row.marka]));
  return priceRows.reduce((acc, row) => {
    const brand = stationBrand.get(row.istasyon_id) || 'Bilinmeyen';
    if (!acc[brand]) {
      acc[brand] = { prices: 0, unknownPrices: 0, latest: null, fuels: new Map() };
    }
    acc[brand].prices += 1;
    if (row.price_status === 'unknown') acc[brand].unknownPrices += 1;
    acc[brand].fuels.set(row.yakit_tipi, (acc[brand].fuels.get(row.yakit_tipi) || 0) + 1);
    // Tazelik "son doğrulama"ya bakar, "son değişim"e değil: fiyat aylarca
    // değişmeden doğru kalabilir (bkz. database/add_price_verification.sql).
    const verifiedAt = row.son_dogrulama || row.son_guncelleme;
    if (!acc[brand].latest || new Date(verifiedAt) > new Date(acc[brand].latest)) {
      acc[brand].latest = verifiedAt;
    }
    return acc;
  }, {});
}

function statusTone({ openAlerts, staleBrands, latestNews }) {
  const newsAge = ageHours(latestNews?.tarih);
  if (openAlerts.some((alert) => ['critical', 'error'].includes(alert.severity))) return 'bad';
  if (staleBrands.length > 0 || (newsAge !== null && newsAge > NEWS_STALE_HOURS)) return 'warn';
  if (openAlerts.length > 0) return 'warn';
  return 'good';
}

function latestRunsByBot(runs) {
  const seen = new Set();
  return runs.filter((run) => {
    const key = `${run.bot_name}:${run.run_mode || '-'}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

function runTone(status) {
  if (status === 'success') return 'good';
  if (status === 'timeout' || status === 'skipped') return 'warn';
  return 'bad';
}

function App() {
  const [session, setSession] = useState(null);
  const [email, setEmail] = useState('');
  const [authMessage, setAuthMessage] = useState('');
  const [isAdmin, setIsAdmin] = useState(false);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState('');
  const [data, setData] = useState({
    heartbeats: [],
    botRuns: [],
    alerts: [],
    news: [],
    stations: [],
    prices: [],
  });

  useEffect(() => {
    if (!supabase) {
      setLoading(false);
      return undefined;
    }

    supabase.auth.getSession().then(({ data: authData }) => {
      setSession(authData.session || null);
      if (authData.session) clearAuthErrorHash();
      setLoading(false);
    });

    const { data: listener } = supabase.auth.onAuthStateChange((_event, nextSession) => {
      setSession(nextSession);
      if (nextSession) clearAuthErrorHash();
    });

    return () => listener.subscription.unsubscribe();
  }, []);

  useEffect(() => {
    if (!session?.user?.email) {
      setIsAdmin(false);
      return;
    }
    checkAdmin(session.user.email);
  }, [session]);

  async function checkAdmin(userEmail) {
    setError('');
    const { data: rows, error: adminError } = await supabase
      .from('admin_emails')
      .select('email')
      .eq('email', userEmail)
      .limit(1);

    if (adminError) {
      setError(`Admin yetkisi okunamadı: ${adminError.message}`);
      setIsAdmin(false);
      return;
    }

    const allowed = (rows || []).length > 0;
    setIsAdmin(allowed);
    if (allowed) {
      await loadDashboard();
    }
  }

  async function sendMagicLink(event) {
    event.preventDefault();
    setAuthMessage('');
    setError('');
    const { error: signInError } = await supabase.auth.signInWithOtp({
      email,
      options: {
        emailRedirectTo: new URL(import.meta.env.BASE_URL, window.location.origin).toString(),
      },
    });
    if (signInError) {
      setError(signInError.message);
    } else {
      setAuthMessage('Giriş linki e-postana gönderildi.');
    }
  }

  async function signOut() {
    await supabase.auth.signOut();
    setSession(null);
    setIsAdmin(false);
    setData({ heartbeats: [], botRuns: [], alerts: [], news: [], stations: [], prices: [] });
  }

  async function loadDashboard() {
    setRefreshing(true);
    setError('');
    try {
      const queries = [
        {
          key: 'heartbeats',
          label: 'Aktif cihazlar',
          query: supabase
          .from('app_heartbeats')
          .select('install_id, first_seen, last_seen, app_version, platform, heartbeat_count')
          .order('last_seen', { ascending: false })
          .limit(5000),
        },
        {
          key: 'botRuns',
          label: 'Bot logları',
          query: supabase
          .from('bot_runs')
          .select('id, bot_name, run_mode, status, started_at, finished_at, duration_seconds, exit_code, summary')
          .order('created_at', { ascending: false })
          .limit(60),
        },
        {
          key: 'alerts',
          label: 'Alarmlar',
          query: supabase
          .from('system_alerts')
          .select('id, severity, source, title, message, status, created_at, resolved_at')
          .order('created_at', { ascending: false })
          .limit(80),
        },
        {
          key: 'news',
          label: 'Haberler',
          query: supabase
          .from('haberler')
          .select('baslik, kaynak, tarih, link')
          .order('tarih', { ascending: false })
          .limit(20),
        },
        {
          key: 'stations',
          label: 'İstasyonlar',
          query: fetchAllRows(() => supabase
            .from('istasyonlar')
            .select('id, marka, il, aktif, visibility_status')
            .order('marka', { ascending: true })
            .order('id', { ascending: true })),
        },
        {
          key: 'prices',
          label: 'Fiyatlar',
          query: fetchAllRows(() => supabase
            .from('fiyatlar')
            .select('istasyon_id, yakit_tipi, son_guncelleme, son_dogrulama, price_status')
            .order('id', { ascending: true })),
        },
      ];

      const results = await Promise.all(queries.map((item) => item.query));
      const nextData = {
        heartbeats: [],
        botRuns: [],
        alerts: [],
        news: [],
        stations: [],
        prices: [],
      };
      const failedMessages = [];

      results.forEach((result, index) => {
        const query = queries[index];
        if (result.error) {
          failedMessages.push(`${query.label}: ${result.error.message}`);
          return;
        }
        nextData[query.key] = result.data || [];
      });

      setData(nextData);
      if (failedMessages.length > 0) {
        setError(`Bazı admin verileri okunamadı: ${failedMessages.join(' | ')}`);
      }
    } catch (loadError) {
      setError(loadError.message || String(loadError));
    } finally {
      setRefreshing(false);
    }
  }

  const metrics = useMemo(() => {
    const now = Date.now();
    const activeNowCutoff = now - ACTIVE_NOW_MINUTES * 60 * 1000;
    const active24Cutoff = now - 24 * 60 * 60 * 1000;
    const active7Cutoff = now - 7 * 24 * 60 * 60 * 1000;
    const active30Cutoff = now - 30 * 24 * 60 * 60 * 1000;
    const stationStats = normalizeStationRows(data.stations);
    const priceStats = normalizePriceRows(data.prices, data.stations);
    const openAlerts = data.alerts.filter((alert) => alert.status === 'open');
    const latestNews = data.news[0] || null;
    const staleBrands = BRANDS.filter((brand) => {
      const latest = priceStats[brand]?.latest;
      const hours = ageHours(latest);
      return hours === null || hours > PRICE_STALE_HOURS;
    });

    return {
      activeNow: data.heartbeats.filter((row) => isAfter(row.last_seen, activeNowCutoff)).length,
      active24h: data.heartbeats.filter((row) => isAfter(row.last_seen, active24Cutoff)).length,
      active7d: data.heartbeats.filter((row) => isAfter(row.last_seen, active7Cutoff)).length,
      active30d: data.heartbeats.filter((row) => isAfter(row.last_seen, active30Cutoff)).length,
      totalDevices: data.heartbeats.length,
      stationStats,
      priceStats,
      openAlerts,
      latestNews,
      staleBrands,
      latestBotRuns: latestRunsByBot(data.botRuns),
      tone: statusTone({ openAlerts, staleBrands, latestNews }),
    };
  }, [data]);

  if (!hasSupabaseConfig) {
    return (
      <Shell>
        <EmptyState
          title="Supabase ayarı eksik"
          text="admin_panel/.env dosyasına VITE_SUPABASE_URL ve VITE_SUPABASE_ANON_KEY ekle."
        />
      </Shell>
    );
  }

  if (loading) {
    return (
      <Shell>
        <EmptyState title="Yükleniyor" text="Oturum kontrol ediliyor." />
      </Shell>
    );
  }

  if (!session) {
    return (
      <Shell compact>
        <section className="login-panel">
          <Shield size={32} />
          <h1>Fullet Admin</h1>
          <p>Panel sadece admin e-posta adresleri için açıktır.</p>
          <form onSubmit={sendMagicLink}>
            <input
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="admin@email.com"
              required
            />
            <button type="submit">Giriş Linki Gönder</button>
          </form>
          {authMessage && <p className="success-text">{authMessage}</p>}
          {error && <p className="error-text">{error}</p>}
        </section>
      </Shell>
    );
  }

  if (!isAdmin) {
    return (
      <Shell>
        <TopBar onRefresh={loadDashboard} onSignOut={signOut} refreshing={refreshing} />
        <EmptyState
          title="Admin yetkisi yok"
          text={`${session.user.email} adresini public.admin_emails tablosuna eklemen gerekiyor.`}
        />
      </Shell>
    );
  }

  return (
    <Shell>
      <TopBar onRefresh={loadDashboard} onSignOut={signOut} refreshing={refreshing} email={session.user.email} />
      {error && <div className="banner danger">{error}</div>}

      <section className={`status-strip ${metrics.tone}`}>
        <div>
          <span className="eyebrow">Genel durum</span>
          <h1>{metrics.tone === 'good' ? 'Sistem temiz' : metrics.tone === 'warn' ? 'Kontrol gerekli' : 'Acil müdahale'}</h1>
        </div>
        <div className="status-meta">
          <span>{metrics.openAlerts.length} açık alarm</span>
          <span>{metrics.staleBrands.length} bayat marka</span>
          <span>Haber: {ageLabel(metrics.latestNews?.tarih)}</span>
        </div>
      </section>

      <section className="metric-grid">
        <Metric icon={Smartphone} label="Şu an aktif" value={metrics.activeNow} detail={`son ${ACTIVE_NOW_MINUTES} dk`} />
        <Metric icon={Activity} label="Bugün aktif" value={metrics.active24h} detail="son 24 saat" />
        <Metric icon={Clock3} label="30 gün aktif" value={metrics.active30d} detail={`toplam ${metrics.totalDevices} cihaz`} />
        <Metric icon={Siren} label="Açık alarm" value={metrics.openAlerts.length} detail="sistem_alerts" />
      </section>

      <section className="dashboard-grid">
        <Panel title="Marka Veri Sağlığı">
          <table>
            <thead>
              <tr>
                <th>Marka</th>
                <th>Aktif / Görünür</th>
                <th>Toplam / Unknown Fiyat</th>
                <th>Son fiyat</th>
                <th>Durum</th>
              </tr>
            </thead>
            <tbody>
              {BRANDS.map((brand) => {
                const station = metrics.stationStats[brand];
                const price = metrics.priceStats[brand];
                const stale = metrics.staleBrands.includes(brand);
                return (
                  <tr key={brand}>
                    <td>{brand}</td>
                    <td>{station?.active || 0} / {station?.visible || 0}</td>
                    <td>{price?.prices || 0} / {price?.unknownPrices || 0}</td>
                    <td>{ageLabel(price?.latest)}</td>
                    <td><Badge tone={stale ? 'warn' : 'good'}>{stale ? 'Bayat' : 'Temiz'}</Badge></td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </Panel>

        <Panel title="Son Bot Durumu">
          <div className="run-list">
            {metrics.latestBotRuns.slice(0, 12).map((run) => (
              <div className="run-row" key={run.id}>
                <div>
                  <strong>{run.bot_name}</strong>
                  <span>{run.run_mode || '-'} · {ageLabel(run.finished_at || run.started_at)}</span>
                </div>
                <Badge tone={runTone(run.status)}>{run.status}</Badge>
              </div>
            ))}
            {metrics.latestBotRuns.length === 0 && <p className="muted">Henüz bot logu yok.</p>}
          </div>
        </Panel>

        <Panel title="Açık Alarmlar">
          <div className="alert-list">
            {metrics.openAlerts.slice(0, 10).map((alert) => (
              <div className="alert-row" key={alert.id}>
                <AlertTriangle size={18} />
                <div>
                  <strong>{alert.title}</strong>
                  <span>{alert.source} · {alert.message}</span>
                </div>
                <Badge tone={alert.severity === 'error' || alert.severity === 'critical' ? 'bad' : 'warn'}>{alert.severity}</Badge>
              </div>
            ))}
            {metrics.openAlerts.length === 0 && <p className="muted">Açık alarm yok.</p>}
          </div>
        </Panel>

        <Panel title="Haber Akışı">
          <div className="news-list">
            {data.news.slice(0, 8).map((news) => (
              <a href={news.link} target="_blank" rel="noreferrer" key={news.link}>
                <strong>{news.baslik}</strong>
                <span>{news.kaynak} · {ageLabel(news.tarih)}</span>
              </a>
            ))}
          </div>
        </Panel>
      </section>
    </Shell>
  );
}

function Shell({ children, compact = false }) {
  return <main className={compact ? 'shell compact' : 'shell'}>{children}</main>;
}

function TopBar({ onRefresh, onSignOut, refreshing, email }) {
  return (
    <header className="topbar">
      <div>
        <span className="eyebrow">Fullet Operasyon</span>
        <h1>Admin Panel</h1>
        {email && <p>{email}</p>}
      </div>
      <div className="topbar-actions">
        <button type="button" onClick={onRefresh} disabled={refreshing}>
          <RefreshCw size={18} />
          Yenile
        </button>
        <button type="button" onClick={onSignOut}>
          <LogOut size={18} />
          Çıkış
        </button>
      </div>
    </header>
  );
}

function Metric({ icon: Icon, label, value, detail }) {
  return (
    <article className="metric">
      <Icon size={20} />
      <span>{label}</span>
      <strong>{value}</strong>
      <small>{detail}</small>
    </article>
  );
}

function Panel({ title, children }) {
  return (
    <section className="panel">
      <h2>{title}</h2>
      {children}
    </section>
  );
}

function Badge({ tone, children }) {
  return <span className={`badge ${tone}`}>{children}</span>;
}

function EmptyState({ title, text }) {
  return (
    <section className="empty-state">
      <CheckCircle2 size={32} />
      <h1>{title}</h1>
      <p>{text}</p>
    </section>
  );
}

export default App;
