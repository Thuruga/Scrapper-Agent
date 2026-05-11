/* eslint-disable @typescript-eslint/no-explicit-any */
import React, { useState, useEffect, useRef } from 'react';
import {
  LayoutDashboard,
  Search,
  Layers,
  Plus as PlusIcon,
  Zap,
  Clock,
  Package,
  CheckCircle2,
  Trash2,
  Plus,
  RefreshCw,
  Terminal,
  XCircle,
  Globe,
  TrendingUp,
  ExternalLink
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer
} from 'recharts';
import { ApiClient } from './api/client';
import './App.css';

// --- Components ---

const LoginView = ({ onLogin }: { onLogin: (token: string) => void }) => {
  const [username, setUsername] = useState('admin');
  const [password, setPassword] = useState('admin123');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      const formData = new FormData();
      formData.append('username', username);
      formData.append('password', password);

      const res = await ApiClient.login(formData);
      onLogin(res.access_token);
    } catch (err: any) {
      setError(err.message || 'Falha ao entrar. Verifique suas credenciais.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-container">
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        className="login-card"
      >
        <div className="login-header">
          <div className="login-logo">
            <Zap size={32} className="text-accent" />
          </div>
          <h1>Intelligence Scraper</h1>
          <p>Faça login para acessar o painel administrativo</p>
        </div>

        <form onSubmit={handleSubmit} className="form-stack">
          {error && <div className="status-banner error">{error}</div>}

          <div className="form-group">
            <label className="label">Usuário</label>
            <input
              type="text"
              className="input"
              value={username}
              onChange={e => setUsername(e.target.value)}
              required
            />
          </div>

          <div className="form-group">
            <label className="label">Senha</label>
            <input
              type="password"
              className="input"
              value={password}
              onChange={e => setPassword(e.target.value)}
              required
            />
          </div>

          <button className="btn btn-primary w-full" disabled={loading} style={{ marginTop: '12px' }}>
            {loading ? <RefreshCw className="animate-spin" size={18} /> : 'Entrar no Sistema'}
          </button>
        </form>

        <div className="login-footer">
          <p>&copy; {new Date().getFullYear()} Thuruga Intelligence.</p>
        </div>
      </motion.div>
    </div>
  );
};


const SidebarItem = ({ icon: Icon, label, active, onClick }: any) => (
  <button
    type="button"
    onClick={onClick}
    className={`sidebar-item ${active ? 'active' : ''}`}
  >
    <Icon size={20} />
    <span>{label}</span>
  </button>
);

const GlassCard = ({ children, title, className = "", subtitle }: any) => (
  <motion.div
    initial={{ opacity: 0, y: 20 }}
    animate={{ opacity: 1, y: 0 }}
    className={`glass-card ${className}`}
  >
    {title && (
      <div className="card-header">
        <h3 className="card-title">{title}</h3>
        {subtitle && <p className="card-subtitle">{subtitle}</p>}
      </div>
    )}
    {children}
  </motion.div>
);

const StatusBanner = ({ type, message, onClear }: { type: 'success' | 'error' | 'info', message: string, onClear?: () => void }) => {
  useEffect(() => {
    if (message && onClear) {
      const timer = setTimeout(onClear, 5000);
      return () => clearTimeout(timer);
    }
  }, [message, onClear]);

  if (!message) return null;

  return (
    <div className={`status-banner ${type}`}>
      {type === 'success' && <CheckCircle2 size={18} />}
      {type === 'error' && <XCircle size={18} />}
      {type === 'info' && <RefreshCw className="animate-spin" size={18} />}
      <span>{message}</span>
    </div>
  );
};


const PriceChart = ({ history }: { history: any[] }) => {
  if (!history || history.length === 0) {
    return (
      <div className="monitor-chart-container">
        <p className="text-muted" style={{ fontSize: '12px', padding: '20px', textAlign: 'center', background: 'rgba(0,0,0,0.1)', borderRadius: '8px', marginTop: '12px' }}>
          Aguardando primeira variação de preço para gerar o gráfico...
        </p>
      </div>
    );
  }

  const data = history.map(h => ({
    time: new Date(h.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    fullDate: new Date(h.timestamp).toLocaleString(),
    price: h.price
  }));

  // Se tiver apenas 1 ponto, duplicamos para mostrar uma linha estável
  const chartData = data.length === 1 ? [data[0], { ...data[0], time: 'Agora' }] : data;

  return (
    <motion.div
      initial={{ opacity: 0, height: 0 }}
      animate={{ opacity: 1, height: 'auto' }}
      className="monitor-chart-container"
      style={{ marginTop: '16px', background: 'rgba(0,0,0,0.2)', borderRadius: '12px', padding: '16px' }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '12px', fontSize: '11px', color: 'rgba(255,255,255,0.4)' }}>
        <span>Histórico de Variações</span>
        <span>{data.length} registros</span>
      </div>
      <div style={{ width: '100%', height: 180 }}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
            <XAxis
              dataKey="time"
              stroke="rgba(255,255,255,0.3)"
              fontSize={10}
              tickLine={false}
              axisLine={false}
              dy={10}
            />
            <YAxis
              stroke="rgba(255,255,255,0.3)"
              fontSize={10}
              tickLine={false}
              axisLine={false}
              tickFormatter={(value) => `R$${value}`}
              domain={['auto', 'auto']}
              dx={-10}
            />
            <Tooltip
              contentStyle={{ backgroundColor: 'rgba(20, 20, 30, 0.95)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', fontSize: '11px', color: '#fff' }}
              itemStyle={{ color: '#6366f1' }}
              formatter={(value: any) => [`R$ ${value.toFixed(2)}`, 'Preço']}
              labelFormatter={(label, items) => items[0]?.payload?.fullDate || label}
            />
            <Line
              type="monotone"
              dataKey="price"
              stroke="#6366f1"
              strokeWidth={3}
              dot={{ r: 4, fill: '#6366f1', strokeWidth: 2, stroke: '#fff' }}
              activeDot={{ r: 6, strokeWidth: 0 }}
              animationDuration={1000}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </motion.div>
  );
};


// --- Pages ---

const MonitorPage = ({ brands }: { brands: any[] }) => {
  const [monitors, setMonitors] = useState<any[]>([]);
  const [url, setUrl] = useState('');
  const [brand, setBrand] = useState('');
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState<{ type: 'success' | 'error' | 'info', message: string } | null>(null);
  const [expandedMonitorId, setExpandedMonitorId] = useState<string | null>(null);

  const refreshMonitors = () => {
    ApiClient.getMonitors().then(data => {
      const list = Array.isArray(data) ? data : Object.values(data);
      setMonitors(list);
    }).catch(() => setMonitors([]));
  };

  useEffect(() => {
    refreshMonitors();
    const intervalId = setInterval(refreshMonitors, 5000);
    return () => clearInterval(intervalId);
  }, []);

  const handleDeleteMonitor = async (jobId: string) => {
    if (!confirm('Deseja excluir este monitor?')) return;
    try {
      await ApiClient.deleteMonitor(jobId);
      refreshMonitors();
      setStatus({ type: 'success', message: 'Monitor excluído!' });
    } catch (err: any) {
      setStatus({ type: 'error', message: 'Erro ao excluir monitor: ' + err.message });
    }
  };

  useEffect(() => {
    if (brands.length > 0 && !brand) {
      setTimeout(() => setBrand(brands[0].brand_key), 0);
    }
  }, [brands, brand]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!url || !brand) return;

    setLoading(true);
    setStatus({ type: 'info', message: 'Iniciando monitoramento...' });

    try {
      await ApiClient.startMonitor({ url, brand });
      setUrl('');
      refreshMonitors();
      setStatus({ type: 'success', message: 'Monitoramento iniciado com sucesso!' });
    } catch (err: any) {
      setStatus({ type: 'error', message: "Erro ao iniciar monitor: " + err.message });
    } finally {
      setLoading(false);
    }
  };


  return (
    <div className="page-content">
      <div className="grid-2">
        <GlassCard title="Monitorar Novo Produto">
          {status && <StatusBanner type={status.type} message={status.message} onClear={() => setStatus(null)} />}
          <form className="form-stack" onSubmit={handleSubmit}>
            <div className="form-group">
              <label className="label">Marca Concorrente</label>
              <select
                className="input"
                value={brand}
                onChange={e => setBrand(e.target.value)}
                required
              >
                <option value="">Selecione...</option>
                {brands && brands.map(b => <option key={b.brand_key} value={b.brand_key}>{b.brand_name}</option>)}
              </select>
            </div>
            <div className="form-group">
              <label className="label">URL do Produto</label>
              <input
                type="url"
                className="input"
                placeholder="https://..."
                value={url}
                onChange={e => setUrl(e.target.value)}
                required
              />
            </div>
            <button className="btn btn-primary w-full" disabled={loading}>
              {loading ? <RefreshCw className="animate-spin" size={18} /> : <Zap size={18} />}
              {loading ? "Iniciando..." : "Iniciar Monitoramento"}
            </button>
          </form>
        </GlassCard>

        <GlassCard title="Lista de Monitoramento">
          <div className="monitor-list">
            {!monitors || monitors.length === 0 ? (
              <div className="empty-state">
                <Clock size={48} className="text-muted" />
                <p>Nenhum monitor ativo no momento.</p>
              </div>
            ) : (
              monitors.map((m: any) => (
                <div key={m.job_id} className="monitor-item">
                  <div className="monitor-image-small">
                    {m.image_url ? <img src={m.image_url} alt={m.product_name} /> : <Package size={24} className="text-muted" />}
                  </div>

                  <div className="monitor-info">
                    <div className="monitor-main">
                      <Package size={14} className="text-accent" />
                      <strong>{m.brand.toUpperCase()}</strong>
                    </div>
                    {m.product_name && <p className="monitor-product-name">{m.product_name}</p>}
                    <span className="monitor-url" title={m.url}>{m.url}</span>
                  </div>

                  <div className="monitor-pricing">
                    {m.last_price ? (
                      <div className="monitor-price-value">R$ {m.last_price.toFixed(2)}</div>
                    ) : (
                      <div className="monitor-price-pending">Pendente...</div>
                    )}
                    <div className="monitor-badge">
                      <span className={`status-dot ${m.active ? 'online' : 'offline'}`}></span>
                      <span>{m.active ? 'Ativo' : 'Inativo'}</span>
                    </div>
                  </div>

                  <div className="monitor-actions">
                    <button
                      className={`btn-icon ${expandedMonitorId === m.job_id ? 'text-accent' : 'text-muted'}`}
                      onClick={() => setExpandedMonitorId(expandedMonitorId === m.job_id ? null : m.job_id)}
                      title="Ver histórico de preços"
                    >
                      <TrendingUp size={20} />
                    </button>
                    <button
                      type="button"
                      className="btn-icon text-error"
                      onClick={() => handleDeleteMonitor(m.job_id)}
                      title="Excluir monitor"
                    >
                      <Trash2 size={18} />
                    </button>
                  </div>

                  <AnimatePresence>
                    {expandedMonitorId === m.job_id && (
                      <div style={{ gridColumn: '1 / -1' }}>
                        <PriceChart history={m.history || []} />
                      </div>
                    )}
                  </AnimatePresence>
                </div>
              ))
            )}
          </div>
        </GlassCard>
      </div>
    </div>
  );
};

const CategoryPage = ({ brands }: { brands: any[] }) => {
  const [selectedBrands, setSelectedBrands] = useState<string[]>([]);
  const [canonicalCategories, setCanonicalCategories] = useState<any[]>([]);
  const [selectedCategory, setSelectedCategory] = useState("");
  const [isScraping, setIsScraping] = useState(false);
  const [logs, setLogs] = useState<any[]>([]);
  const [progress, setProgress] = useState({ current: 0, total: 0, success: 0, error: 0 });
  const [outputFile, setOutputFile] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  const logEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    ApiClient.getCanonicalCategories().then(data => {
      const flat = data.reduce((acc: any[], group: any) => [...acc, ...group.categories], []);
      setCanonicalCategories(flat);
    }).catch(console.error);
  }, []);

  useEffect(() => {
    if (selectedBrands.length === 1) {
      ApiClient.request<any>(`/brands/${selectedBrands[0]}/categories`).then(data => {
        if (data && data.categories) {
          const flat = data.categories.reduce((acc: any[], group: any) => {
            const items = group.items.map((i: any) => ({ slug: i.path, label: `${group.group} - ${i.label}` }));
            return [...acc, ...items];
          }, []);
          setCanonicalCategories(flat);
        }
      }).catch(console.error);
    } else {
      ApiClient.getCanonicalCategories().then(data => {
        const flat = data.reduce((acc: any[], group: any) => [...acc, ...group.categories], []);
        setCanonicalCategories(flat);
      }).catch(console.error);
    }
  }, [selectedBrands]);

  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  const toggleBrand = (key: string) => {
    setSelectedBrands(prev =>
      prev.includes(key) ? prev.filter(k => k !== key) : [...prev, key]
    );
  };

  const startScrape = async () => {
    if (selectedBrands.length === 0 || !selectedCategory) return;

    setIsScraping(true);
    setOutputFile(null);
    setLogs([{ type: 'info', text: `Iniciando varredura para: ${selectedBrands.join(', ')}`, time: new Date().toLocaleTimeString() }]);
    setProgress({ current: 0, total: 0, success: 0, error: 0 });

    try {
      const isMulti = selectedBrands.length > 1;
      let payload: any;

      if (isMulti) {
        payload = { brands: selectedBrands, category_slug: selectedCategory };
      } else {
        const brand = selectedBrands[0];
        // Se a categoria selecionada for uma URL completa, enviamos como custom_url
        if (selectedCategory.startsWith('http')) {
          payload = { brand, custom_url: selectedCategory };
        } else {
          payload = { brand, category_path: selectedCategory };
        }
      }

      const res: any = await ApiClient.startScrape(payload, isMulti);
      const jobId = res.job_id;

      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const ws = new WebSocket(`${protocol}//${window.location.host}/ws/${jobId}?token=${ApiClient.getToken()}`);
      wsRef.current = ws;

      ws.onmessage = (e) => {
        const msg = JSON.parse(e.data);
        if (msg.type === 'brand_success') {
          setProgress(prev => ({ ...prev, current: prev.current + 1, success: prev.success + 1 }));
        } else if (msg.type === 'brand_error') {
          setProgress(prev => ({ ...prev, current: prev.current + 1, error: prev.error + 1 }));
        } else if (msg.type === 'done' || msg.type === 'error_done') {
          setIsScraping(false);
          ws.close();
          if (msg.output_file) {
            setOutputFile(msg.output_file);
          }
        }

        if (msg.message) {
          setLogs(prev => [...prev, { type: msg.type || 'info', text: msg.message, time: new Date().toLocaleTimeString() }]);
        }
      };
    } catch (err: any) {
      setLogs(prev => [...prev, { type: 'error', text: `Erro: ${err.message}`, time: new Date().toLocaleTimeString() }]);
      setIsScraping(false);
    }
  };






  return (
    <div className="page-content">
      <div className="grid-category">
        <div className="category-sidebar">
          <GlassCard title="Configuração da Varredura">
            <div className="form-stack">
              <div className="form-group">
                <label className="label">Marcas Alvo</label>
                <div className="brand-selector-grid">
                  {brands.map(b => (
                    <button
                      type="button"
                      key={b.brand_key}
                      className={`brand-chip ${selectedBrands.includes(b.brand_key) ? 'active' : ''}`}
                      onClick={() => toggleBrand(b.brand_key)}
                    >
                      <div className="brand-chip-icon">
                        <img
                          src={b.logo_url || `https://www.google.com/s2/favicons?domain=${b.domain}&sz=64`}
                          alt={b.brand_name}
                          onError={(e: any) => { e.target.src = `https://ui-avatars.com/api/?name=${b.brand_name}&background=6366f1&color=fff`; }}
                        />
                      </div>
                      <span>{b.brand_name}</span>
                    </button>
                  ))}
                </div>
              </div>

              <div className="form-group">
                <label className="label">Categoria</label>
                <select
                  className="input"
                  value={selectedCategory}
                  onChange={e => setSelectedCategory(e.target.value)}
                >
                  <option value="">Selecione...</option>
                  {canonicalCategories.map((cat: any) => (
                    <option key={cat.slug} value={cat.slug}>{cat.label}</option>
                  ))}
                </select>
              </div>

              <button
                className="btn btn-primary w-full"
                onClick={startScrape}
                disabled={isScraping || selectedBrands.length === 0 || !selectedCategory}
              >
                {isScraping ? <RefreshCw className="animate-spin" size={18} /> : <Zap size={18} />}
                {isScraping ? "Processando..." : "Iniciar Varredura"}
              </button>


            </div>
          </GlassCard>


        </div>


        <div className="category-main">
          <GlassCard title="Progresso e Logs" subtitle={isScraping ? "Acompanhando em tempo real..." : "Aguardando início..."}>
            <div className="scrape-stats">
              {/* Total Detectado removido conforme solicitado */}
              <div className="stat-box">
                <span className="stat-label">Total</span>
                <span className="stat-value">{progress.current}</span>
              </div>
              <div className="stat-box">
                <span className="stat-label text-success">Sucessos</span>
                <span className="stat-value text-success">{progress.success}</span>
              </div>
              <div className="stat-box">
                <span className="stat-label text-error">Falhas</span>
                <span className="stat-value text-error">{progress.error}</span>
              </div>
            </div>

            <div className="progress-bar-large">
              <div
                className="progress-fill-large"
                style={{ width: `${progress.current > 0 ? (progress.success / progress.current) * 100 : 0}%` }}
              />
            </div>

            <div className="console-container">
              <div className="console-header">
                <Terminal size={14} />
                <span>Console Feed</span>
              </div>
              <div className="console-body">
                {logs.length === 0 && <div className="console-empty">Aguardando comandos...</div>}
                {logs.map((log, i) => (
                  <div key={i} className={`console-line ${log.type}`}>
                    <span className="log-time">[{log.time}]</span>
                    <span className="log-text">{log.text}</span>
                  </div>
                ))}
                <div ref={logEndRef} />
              </div>
            </div>

            {outputFile && (
              <div style={{ marginTop: '16px', display: 'flex', justifyContent: 'flex-end' }}>
                <a
                  href={`${import.meta.env.VITE_API_URL || ''}/download-report/${outputFile}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="btn btn-primary"
                >
                  <Package size={18} /> Baixar Relatório (Excel)
                </a>
              </div>
            )}
          </GlassCard>
        </div>
      </div>
    </div>
  );
};

const SearchPage = ({ brands }: { brands: any[] }) => {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [sort, setSort] = useState('relevance');
  const [inStock, setInStock] = useState(false);
  const [selectedBrands, setSelectedBrands] = useState<string[]>([]);

  const toggleBrand = (key: string) => {
    setSelectedBrands(prev =>
      prev.includes(key) ? prev.filter(k => k !== key) : [...prev, key]
    );
  };

  const selectAllBrands = () => {
    setSelectedBrands(brands.map(b => b.brand_key));
  };

  const clearBrands = () => {
    setSelectedBrands([]);
  };

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      const data = await ApiClient.search({
        query,
        sort,
        only_in_stock: inStock,
        brands: selectedBrands.length > 0 ? selectedBrands : undefined
      });
      setResults(data);
    } catch (err) {
      console.error(err);
      setResults(null);
    } finally {
      setLoading(false);
    }
  };

  const handleExport = async () => {
    if (!query) return;
    setExporting(true);
    try {
      await ApiClient.exportSearch({
        query,
        sort,
        only_in_stock: inStock,
        brands: selectedBrands.length > 0 ? selectedBrands : undefined
      });
    } catch (err: any) {
      console.error(err);
      alert("Erro ao exportar: " + err.message);
    } finally {
      setExporting(false);
    }
  };

  return (
    <div className="page-content">
      <GlassCard className="search-bar-container">
        <form onSubmit={handleSearch} className="search-form">
          <div className="search-input-wrapper">
            <Search className="search-icon" size={20} />
            <input
              type="text"
              className="search-input"
              placeholder="Ex: Polo Piquet, Camisa Social..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
          </div>
          <div className="search-filters">
            <select className="input input-sm" value={sort} onChange={e => setSort(e.target.value)}>
              <option value="relevance">Relevância</option>
              <option value="price_asc">Menor Preço</option>
              <option value="price_desc">Maior Preço</option>
              <option value="top_selling">Mais Vendidos</option>
            </select>
            <label className="checkbox-label">
              <input type="checkbox" checked={inStock} onChange={e => setInStock(e.target.checked)} />
              <span>Em estoque</span>
            </label>
            <div style={{ display: 'flex', gap: '8px' }}>
              <button type="submit" className="btn btn-primary" disabled={loading || exporting}>
                {loading ? <RefreshCw className="animate-spin" size={18} /> : "Comparar"}
              </button>
              <button type="button" className="btn btn-secondary" onClick={handleExport} disabled={loading || exporting || !query} title="Exportar para Excel">
                {exporting ? <RefreshCw className="animate-spin" size={18} /> : <Package size={18} />}
              </button>
            </div>
          </div>
        </form>

        <div className="divider" style={{ margin: '16px 0', opacity: 0.2 }} />

        <div className="form-group" style={{ marginBottom: 0 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
            <label className="label" style={{ marginBottom: 0, display: 'flex', alignItems: 'center', gap: '8px' }}>
              Filtro de Marcas
              <span className="text-muted" style={{ fontSize: '0.8em', fontWeight: 'normal' }}>
                ({selectedBrands.length === 0 ? 'Buscando em todas as marcas' : `${selectedBrands.length} marca(s) selecionada(s)`})
              </span>
            </label>
            <div style={{ display: 'flex', gap: '8px' }}>
              <button type="button" className="btn btn-sm btn-outline" onClick={selectAllBrands} style={{ padding: '4px 8px', fontSize: '12px', minHeight: 'unset' }}>Selecionar Todas</button>
              <button type="button" className="btn btn-sm btn-outline" onClick={clearBrands} style={{ padding: '4px 8px', fontSize: '12px', minHeight: 'unset' }}>Limpar</button>
            </div>
          </div>

          <div className="brand-selector-grid" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(150px, 1fr))' }}>
            {brands.map(b => (
              <button
                type="button"
                key={b.brand_key}
                className={`brand-chip ${selectedBrands.includes(b.brand_key) ? 'active' : ''}`}
                onClick={() => toggleBrand(b.brand_key)}
              >
                <div className="brand-chip-icon">
                  <img
                    src={b.logo_url || `https://www.google.com/s2/favicons?domain=${b.domain}&sz=64`}
                    alt={b.brand_name}
                    onError={(e: any) => { e.target.src = `https://ui-avatars.com/api/?name=${b.brand_name}&background=6366f1&color=fff`; }}
                  />
                </div>
                <span>{b.brand_name}</span>
              </button>
            ))}
          </div>
        </div>
      </GlassCard>

      <div className="results-container">
        {results && results.results && Array.isArray(results.results) && results.results.map((brandRes: any) => (
          <div key={brandRes.brand_key} className="brand-column">
            <h4 className="brand-header">{brandRes.brand_name}</h4>
            <div className="product-grid">
              {brandRes.products?.map((p: any) => (
                <a
                  key={p.url}
                  href={p.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="product-card"
                >
                  <div className="product-image">
                    {p.image_url ? <img src={p.image_url} alt={p.product_name} /> : <Package size={40} />}
                    {p.price_discount && <span className="badge-discount">OFF</span>}
                  </div>
                  <div className="product-details">
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '8px' }}>
                      <p className="product-name">{p.product_name}</p>
                      <ExternalLink size={14} className="text-muted" style={{ marginTop: '4px', flexShrink: 0 }} />
                    </div>
                    <div className="product-price">
                      <span className="price-current">R$ {p.price_full.toFixed(2)}</span>
                    </div>
                    <div className="product-meta">
                      {p.available ? <CheckCircle2 size={14} className="text-success" /> : <XCircle size={14} className="text-error" />}
                      <span>{p.available ? 'Em estoque' : 'Esgotado'}</span>
                    </div>
                  </div>
                </a>
              ))}
              {(!brandRes.products || brandRes.products.length === 0) && (
                <div className="empty-column">Nenhum resultado</div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

const SettingsPage = ({ brands, onRefresh }: { brands: any[], onRefresh: () => void }) => {
  const [newBrand, setNewBrand] = useState({ brand_key: '', brand_name: '', domain: '', logo_url: '', engine: 'vtex' });
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState<{ type: 'success' | 'error' | 'info', message: string } | null>(null);

  const handleDeleteBrand = async (key: string) => {
    if (!confirm(`Tem certeza que deseja excluir a marca ${key}?`)) return;
    try {
      await ApiClient.deleteBrand(key);
      onRefresh();
    } catch (err: any) {
      alert("Erro ao excluir: " + err.message);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      await ApiClient.saveBrand(newBrand);
      setNewBrand({ brand_key: '', brand_name: '', domain: '', logo_url: '', engine: 'vtex' });
      onRefresh();
      setStatus({ type: 'success', message: 'Marca cadastrada com sucesso!' });
    } catch (err: any) {
      setStatus({ type: 'error', message: err.message });
    } finally {
      setLoading(false);
    }
  };


  return (
    <div className="page-content">
      <div className="grid-2">
        <GlassCard title="Cadastrar Nova Marca">
          {status && <StatusBanner type={status.type} message={status.message} onClear={() => setStatus(null)} />}
          <form onSubmit={handleSubmit} className="form-stack">
            <div className="form-group">
              <label className="label">ID Interno (Slug)</label>
              <input
                type="text"
                className="input"
                placeholder="ex: brooksfield"
                value={newBrand.brand_key}
                onChange={e => setNewBrand({ ...newBrand, brand_key: e.target.value })}
                required
              />
            </div>
            <div className="form-group">
              <label className="label">Nome da Marca</label>
              <input
                type="text"
                className="input"
                placeholder="ex: Brooksfield Menswear"
                value={newBrand.brand_name}
                onChange={e => setNewBrand({ ...newBrand, brand_name: e.target.value })}
                required
              />
            </div>
            <div className="form-group">
              <label className="label">Domínio (sem https)</label>
              <input
                type="text"
                className="input"
                placeholder="ex: www.brooksfield.com.br"
                value={newBrand.domain}
                onChange={e => setNewBrand({ ...newBrand, domain: e.target.value })}
                required
              />
            </div>
            <button className="btn btn-primary w-full" disabled={loading}>
              {loading ? <RefreshCw className="animate-spin" size={18} /> : <Plus size={18} />}
              Cadastrar Marca
            </button>
          </form>
        </GlassCard>

        <GlassCard title="Marcas Cadastradas">
          <div className="brand-list">
            {brands.map(b => (
              <div key={b.brand_key} className="brand-item">
                <div className="brand-info">
                  <div className="brand-avatar">
                    <img
                      src={b.logo_url || `https://www.google.com/s2/favicons?domain=${b.domain}&sz=64`}
                      alt={b.brand_name}
                      onError={(e: any) => { e.target.src = `https://ui-avatars.com/api/?name=${b.brand_name}&background=6366f1&color=fff`; }}
                    />
                  </div>
                  <div>
                    <p className="brand-name-text">{b.brand_name}</p>
                    <p className="brand-domain-text"><Globe size={12} /> {b.domain}</p>
                  </div>
                </div>
                <div className="brand-actions">
                  <button
                    type="button"
                    className="btn-icon text-error"
                    onClick={() => handleDeleteBrand(b.brand_key)}
                  >
                    <Trash2 size={18} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </GlassCard>
      </div>
    </div>
  );
};


// --- Main App ---

function App() {
  const [activeTab, setActiveTab] = useState('monitor');
  const [brands, setBrands] = useState<any[]>([]);
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(!!ApiClient.getToken());

  const refreshBrands = () => {
    if (!isAuthenticated) return;
    ApiClient.getBrands().then(data => {
      if (Array.isArray(data)) setBrands(data);
    }).catch(err => {
      console.error(err);
      if (err.message.includes('401')) setIsAuthenticated(false);
    });
  };

  useEffect(() => {
    const handleAuthExpired = () => setIsAuthenticated(false);
    window.addEventListener('auth-expired', handleAuthExpired);

    if (isAuthenticated) {
      refreshBrands();
    }

    return () => window.removeEventListener('auth-expired', handleAuthExpired);
  }, [isAuthenticated]);

  const handleLogin = (_token: string) => {
    setIsAuthenticated(true);
  };

  const handleLogout = () => {
    ApiClient.clearToken();
    setIsAuthenticated(false);
  };

  if (!isAuthenticated) {
    return <LoginView onLogin={handleLogin} />;
  }

  const renderTab = () => {
    switch (activeTab) {
      case 'monitor': return <MonitorPage brands={brands} />;
      case 'search': return <SearchPage brands={brands} />;
      case 'category': return <CategoryPage brands={brands} />;
      case 'settings': return <SettingsPage brands={brands} onRefresh={refreshBrands} />;
      default: return <div className="p-8">Selecione uma aba...</div>;
    }
  };

  return (
    <div className="app-container">
      <aside className="sidebar">
        <div className="sidebar-header">
          <div className="logo-icon"><Zap size={24} fill="white" /></div>
          <h2>E-Scraper</h2>
        </div>
        <nav className="sidebar-nav">
          <SidebarItem
            icon={LayoutDashboard}
            label="Monitores"
            active={activeTab === 'monitor'}
            onClick={() => setActiveTab('monitor')}
          />
          <SidebarItem
            icon={Search}
            label="Comparativo"
            active={activeTab === 'search'}
            onClick={() => setActiveTab('search')}
          />
          <SidebarItem
            icon={Layers}
            label="Categorias"
            active={activeTab === 'category'}
            onClick={() => setActiveTab('category')}
          />
          <div className="sidebar-spacer" />
          <SidebarItem
            icon={PlusIcon}
            label="Marcas"
            active={activeTab === 'settings'}
            onClick={() => setActiveTab('settings')}
          />
        </nav>
      </aside>

      <main className="main-content">
        <header className="content-header">
          <div>
            <h1>{
              activeTab === 'monitor' ? 'Painel de Monitoramento' :
                activeTab === 'search' ? 'Busca Comparativa' :
                  activeTab === 'category' ? 'Varredura por Categoria' :
                    'Adicionar Marca'
            }
            </h1>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
            <div className="user-badge">
              <CheckCircle2 size={14} className="text-success" />
              <span>Server Online</span>
            </div>
            <button onClick={handleLogout} className="btn-icon text-muted" title="Sair">
              <XCircle size={20} />
            </button>
          </div>
        </header>

        <AnimatePresence mode="wait">
          <motion.div
            key={activeTab}
            initial={{ opacity: 0, x: 10 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -10 }}
            transition={{ duration: 0.2 }}
          >
            {renderTab()}
          </motion.div>
        </AnimatePresence>
      </main>
    </div>
  );
}

export default App;
