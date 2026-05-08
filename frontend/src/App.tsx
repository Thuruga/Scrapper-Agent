/* eslint-disable @typescript-eslint/no-explicit-any */
import React, { useState, useEffect, useRef } from 'react';
import {
  LayoutDashboard,
  Search,
  Layers,
  Settings as SettingsIcon,
  Zap,
  Clock,
  Package,
  CheckCircle2,
  Trash2,
  Plus,
  RefreshCw,
  Terminal,
  XCircle,
  Globe
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { ApiClient, API_KEY } from './api/client';
import './App.css';

// --- Components ---

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


// --- Pages ---

const MonitorPage = ({ brands }: { brands: any[] }) => {
  const [monitors, setMonitors] = useState<any[]>([]);
  const [url, setUrl] = useState('');
  const [brand, setBrand] = useState('');
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState<{ type: 'success' | 'error' | 'info', message: string } | null>(null);

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
                    {m.image_url ? <img src={m.image_url} alt={m.product_name} /> : <Package size={20} />}
                  </div>
                  <div className="monitor-info">
                    <div className="monitor-main" style={{ display: 'flex', alignItems: 'center', width: '100%', gap: '8px' }}>
                      <Package size={14} className="text-accent" />
                      <strong>{m.brand.toUpperCase()}</strong>
                      <button
                        type="button"
                        className="btn-icon text-error"
                        style={{ marginLeft: 'auto' }}
                        onClick={() => handleDeleteMonitor(m.job_id)}
                        title="Excluir monitor"
                      >
                        <Trash2 size={16} />
                      </button>
                    </div>
                    {m.product_name && <p className="monitor-product-name">{m.product_name}</p>}
                    <span className="monitor-url">{m.url}</span>
                  </div>
                  <div className="monitor-pricing">
                    {m.last_price ? (
                      <div className="monitor-price-value">R$ {m.last_price.toFixed(2)}</div>
                    ) : (
                      <div className="monitor-price-pending">Aguardando...</div>
                    )}
                    <div className="monitor-badge">
                      {m.active ? <span className="status-dot online"></span> : <span className="status-dot offline"></span>}
                      <span>{m.active ? 'Ativo' : 'Inativo'}</span>
                    </div>
                  </div>
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
  const [isDiscovering, setIsDiscovering] = useState(false);
  const [suggestions, setSuggestions] = useState<any[]>([]);
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
      const ws = new WebSocket(`${protocol}//${window.location.host}/ws/${jobId}?api_key=${API_KEY}`);
      wsRef.current = ws;

      ws.onmessage = (e) => {
        const msg = JSON.parse(e.data);
        if (msg.type === 'brand_stats') {
          setProgress(prev => ({ ...prev, total: prev.total + msg.total_links }));
        } else if (msg.type === 'brand_success') {
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

  const handleAutoDiscover = async () => {
    if (selectedBrands.length === 0) return;
    setIsDiscovering(true);
    setLogs(prev => [...prev, { type: 'info', text: "Iniciando descoberta inteligente...", time: new Date().toLocaleTimeString() }]);

    try {
      // Pega sugestões da primeira marca selecionada (para simplificar o MVP)
      const res = await ApiClient.discoverCategories(selectedBrands[0]);
      setSuggestions(res.suggestions || []);
      setLogs(prev => [...prev, { type: 'success', text: `Encontradas ${res.suggestions?.length || 0} sugestões!`, time: new Date().toLocaleTimeString() }]);
    } catch (err: any) {
      setLogs(prev => [...prev, { type: 'error', text: `Erro na descoberta: ${err.message}`, time: new Date().toLocaleTimeString() }]);
    } finally {
      setIsDiscovering(false);
    }
  };

  const handleUseSuggestion = (s: any) => {
    setSelectedCategory(s.canonical_slug);
    setLogs(prev => [...prev, { type: 'info', text: `Usando: ${s.canonical_label} (${s.vtex_path})`, time: new Date().toLocaleTimeString() }]);
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

              <div className="divider" />

              <button
                type="button"
                className="btn btn-secondary w-full"
                onClick={handleAutoDiscover}
                disabled={isDiscovering || selectedBrands.length === 0}
              >
                {isDiscovering ? <RefreshCw className="animate-spin" size={18} /> : <Layers size={18} />}
                {isDiscovering ? "Analisando..." : "Sugerir Categorias"}
              </button>
            </div>
          </GlassCard>

          {suggestions.length > 0 && (
            <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }}>
              <GlassCard title="Sugestões Encontradas" className="mt-4">
                <div className="suggestion-list">
                  {suggestions.map((s, i) => (
                    <div key={i} className="suggestion-item">
                      <div className="suggestion-info">
                        <strong>{s.canonical_label}</strong>
                        <span>{s.vtex_path}</span>
                      </div>
                      <button type="button" className="btn btn-sm btn-outline" onClick={() => handleUseSuggestion(s)}>
                        Usar
                      </button>
                    </div>
                  ))}
                </div>
              </GlassCard>
            </motion.div>
          )}
        </div>


        <div className="category-main">
          <GlassCard title="Progresso e Logs" subtitle={isScraping ? "Acompanhando em tempo real..." : "Aguardando início..."}>
            <div className="scrape-stats">
              <div className="stat-box">
                <span className="stat-label">Total</span>
                <span className="stat-value">{progress.total}</span>
              </div>
              <div className="stat-box">
                <span className="stat-label">Processados</span>
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
                style={{ width: `${progress.total > 0 ? (progress.current / progress.total) * 100 : 0}%` }}
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
                <div key={p.url} className="product-card">
                  <div className="product-image">
                    {p.image_url ? <img src={p.image_url} alt={p.product_name} /> : <Package size={40} />}
                    {p.price_discount && <span className="badge-discount">OFF</span>}
                  </div>
                  <div className="product-details">
                    <p className="product-name">{p.product_name}</p>
                    <div className="product-price">
                      <span className="price-current">R$ {p.price_full.toFixed(2)}</span>
                    </div>
                    <div className="product-meta">
                      {p.available ? <CheckCircle2 size={14} className="text-success" /> : <XCircle size={14} className="text-error" />}
                      <span>{p.available ? 'Em estoque' : 'Esgotado'}</span>
                    </div>
                  </div>
                </div>
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
  const [newBrand, setNewBrand] = useState({ brand_key: '', brand_name: '', domain: '', logo_url: '' });
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
      setNewBrand({ brand_key: '', brand_name: '', domain: '', logo_url: '' });
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
            <div className="form-group">
              <label className="label">URL da Logo (Opcional)</label>
              <input
                type="url"
                className="input"
                placeholder="https://.../logo.png"
                value={newBrand.logo_url}
                onChange={e => setNewBrand({ ...newBrand, logo_url: e.target.value })}
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

  const refreshBrands = () => {
    ApiClient.getBrands().then(data => {
      if (Array.isArray(data)) setBrands(data);
    }).catch(console.error);
  };

  useEffect(() => {
    refreshBrands();
  }, []);

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
            icon={SettingsIcon}
            label="Configurações"
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
                    'Configurações do Sistema'
            }</h1>
            <p className="header-subtitle">Intelligence Scraper</p>
          </div>
          <div className="user-badge">
            <CheckCircle2 size={14} className="text-success" />
            <span>Server Online</span>
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
