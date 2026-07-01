/* eslint-disable @typescript-eslint/no-explicit-any */
import React, { useState, useEffect, useRef } from 'react';
import {
  LayoutDashboard,
  Search,
  Layers,
  Zap,
  Clock,
  Package,
  CheckCircle2,
  Trash2,
  Plus,
  RefreshCw,
  Terminal,
  XCircle,
  Pause,
  Play,
  Globe,
  TrendingUp,
  ExternalLink,
  Download,
  FileSpreadsheet,
  Radar,
  AlertTriangle,
  Eye,
  X,
  Menu,
  ChevronLeft,
  ChevronRight,
  ChevronDown,
  ChevronUp,
  Check,
  Power,
  History,
  Images,
  Square,
  MapPin,
  Truck,
  Gauge,
  MessageSquare,
} from 'lucide-react';
import { toast } from 'sonner';
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
import { useSearchStore, withDisplayOrder } from './stores/searchStore';
import { useBannerStore, type BannerCandidate } from './stores/bannerStore';
import { useShallow } from 'zustand/react/shallow';
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

// Normaliza um domínio para comparação: minúsculas + remove ponto final (FQDN)
// + remove prefixo literal "www." (slice literal, NÃO lstrip — lstrip removeria o
// char-set {w,.} e corromperia hosts).
const normalizeDomain = (domain: string): string => {
  const host = (domain || '').trim().toLowerCase().replace(/\.+$/, '');
  return host.startsWith('www.') ? host.slice('www.'.length) : host;
};

// Casa o host de uma URL com o domínio cadastrado de uma marca.
// Match exato OU por sufixo de LABEL: o domínio cadastrado de marketplace é o
// registrável (ex.: "mercadolivre.com.br"), mas a URL do produto pode vir em
// qualquer subdomínio ("produto.mercadolivre.com.br", "lista.mercadolivre.com.br",
// "www.amazon.com.br", "m.netshoes.com.br"). Sem isto, o identify-first casava só
// por igualdade exata: "produto.mercadolivre.com.br" ≠ "mercadolivre.com.br" ⇒ o
// ML nunca criava monitor (bug monitor-marketplace-pendente Round 2, causa ML).
// Boundary de label (host === base || host.endsWith("." + base)) para NÃO casar
// "maliciousmercadolivre.com.br".
const domainMatchesBrand = (urlDomain: string, brandDomain: string): boolean => {
  const host = normalizeDomain(urlDomain);
  const base = normalizeDomain(brandDomain);
  if (!host || !base) return false;
  return host === base || host.endsWith(`.${base}`);
};

const MonitorPage = ({ brands }: { brands: any[] }) => {
  const [monitors, setMonitors] = useState<any[]>([]);
  const [url, setUrl] = useState('');
  const [brand, setBrand] = useState('');
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState<{ type: 'success' | 'error' | 'info', message: string } | null>(null);
  const [expandedMonitorId, setExpandedMonitorId] = useState<string | null>(null);
  // Identify-first: marca identificada por domínio, e fallback manual quando não há match.
  const [identifiedBrandName, setIdentifiedBrandName] = useState<string | null>(null);
  const [showManualBrand, setShowManualBrand] = useState(false);

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

  const handleToggleActive = async (jobId: string, isActive: boolean) => {
    try {
      if (isActive) {
        await ApiClient.stopMonitor(jobId);
        setStatus({ type: 'success', message: 'Monitoramento desativado.' });
      } else {
        await ApiClient.resumeMonitor(jobId);
        setStatus({ type: 'success', message: 'Monitoramento reativado.' });
      }
      refreshMonitors();
    } catch (err: any) {
      setStatus({ type: 'error', message: 'Erro ao alterar status: ' + err.message });
    }
  };

  useEffect(() => {
    if (brands.length > 0 && !brand) {
      setTimeout(() => setBrand(brands[0].brand_key), 0);
    }
  }, [brands, brand]);

  // Inicia o monitor com dedup + feedback de status (mesma semântica do botão "+" das 3 telas).
  const startMonitorForBrand = async (productUrl: string, brandKey: string, brandLabel?: string) => {
    const result = await ApiClient.addToMonitor(productUrl, brandKey);
    if (result.status === 'already_active') {
      setStatus({ type: 'info', message: 'Produto já está em monitoramento' });
      toast.info('Produto já está em monitoramento');
    } else if (result.status === 'reactivated') {
      setStatus({ type: 'success', message: 'Monitor reativado' });
      toast.success('Monitor reativado');
    } else {
      setStatus({ type: 'success', message: brandLabel ? `Adicionado ao monitoramento (${brandLabel})` : 'Adicionado ao monitoramento' });
      toast.success('Adicionado ao monitoramento');
    }
    setUrl('');
    setShowManualBrand(false);
    setIdentifiedBrandName(null);
    refreshMonitors();
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!url) return;

    // Caminho de fallback manual: o usuário já revelou o select e escolheu a marca.
    if (showManualBrand) {
      if (!brand) {
        setStatus({ type: 'error', message: 'Selecione uma marca para iniciar o monitoramento.' });
        return;
      }
      setLoading(true);
      setStatus({ type: 'info', message: 'Iniciando monitoramento...' });
      try {
        const meta = brands.find(b => b.brand_key === brand);
        await startMonitorForBrand(url, brand, meta?.brand_name);
      } catch (err: any) {
        setStatus({ type: 'error', message: 'Erro ao iniciar monitor: ' + err.message });
        toast.error(err.message || 'Erro ao adicionar ao monitoramento');
      } finally {
        setLoading(false);
      }
      return;
    }

    // Caminho identify-first: cola a URL → detecta o domínio → casa com marca cadastrada.
    setLoading(true);
    setIdentifiedBrandName(null);
    setStatus({ type: 'info', message: 'Identificando marca pelo link...' });
    try {
      const identified = await ApiClient.identifyBrand(url);
      // Casa por sufixo de label (domainMatchesBrand): cobre subdomínios de
      // marketplace (produto./lista./www./m.) sem corromper o match de marcas
      // próprias. O identify devolve o host como veio na URL (ex.:
      // "produto.mercadolivre.com.br"); a marca ML está cadastrada como
      // "mercadolivre.com.br". Igualdade exata falhava e o ML nunca criava monitor.
      const matched = brands.find(b => domainMatchesBrand(identified.domain, b.domain));

      if (matched) {
        setIdentifiedBrandName(matched.brand_name);
        await startMonitorForBrand(url, matched.brand_key, matched.brand_name);
      } else {
        // Sem marca cadastrada para o domínio → NÃO inicia; revela o select manual.
        setIdentifiedBrandName(null);
        setShowManualBrand(true);
        setStatus({
          type: 'info',
          message: 'Não identificamos uma marca cadastrada para este domínio. Selecione a marca manualmente.',
        });
        toast.info('Selecione a marca manualmente para este produto.');
      }
    } catch (err: any) {
      setStatus({ type: 'error', message: 'Erro ao identificar marca: ' + err.message });
      toast.error(err.message || 'Erro ao identificar marca');
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
              <label className="label">URL do Produto</label>
              <input
                type="url"
                className="input"
                placeholder="Cole o link do produto — identificamos a marca automaticamente"
                value={url}
                onChange={e => {
                  setUrl(e.target.value);
                  // Mudar a URL invalida a identificação anterior e volta ao fluxo identify-first.
                  setIdentifiedBrandName(null);
                  setShowManualBrand(false);
                }}
                required
              />
            </div>
            {identifiedBrandName && (
              <p className="text-muted" style={{ fontSize: '13px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <CheckCircle2 size={14} className="text-success" /> Marca identificada: <strong>{identifiedBrandName}</strong>
              </p>
            )}
            {showManualBrand && (
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
            )}
            <button className="btn btn-primary w-full" disabled={loading || !url}>
              {loading ? <RefreshCw className="animate-spin" size={18} /> : <Zap size={18} />}
              {loading ? "Processando..." : showManualBrand ? "Iniciar Monitoramento" : "Identificar e Monitorar"}
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
                    ) : (m.last_status === 'blocked' || m.last_status === 'error') ? (
                      <div
                        className="monitor-price-blocked"
                        title={m.last_error || 'Não foi possível ler o produto.'}
                      >
                        {m.last_status === 'blocked' ? 'Bloqueado (anti-bot)' : 'Indisponível'}
                      </div>
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
                      className={`btn-icon ${m.active ? 'text-error' : 'text-success'}`}
                      onClick={() => handleToggleActive(m.job_id, m.active)}
                      title={m.active ? "Pausar monitoramento" : "Retomar monitoramento"}
                    >
                      {m.active ? <Pause size={18} /> : <Play size={18} />}
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
  const [brandCategories, setBrandCategories] = useState<Record<string, any[]>>({});
  const [brandSelections, setBrandSelections] = useState<Record<string, string>>({});
  const [isScraping, setIsScraping] = useState(false);
  const [logs, setLogs] = useState<any[]>([]);
  const [progress, setProgress] = useState({ current: 0, total: 0, success: 0, error: 0 });
  const [outputFile, setOutputFile] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  const logEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  useEffect(() => {
    return () => {
      if (wsRef.current) {
        // Solta TODOS os handlers antes de fechar (WR-04) — previne setState após unmount
        // e mantém o cleanup robusto caso onopen/onerror/onclose passem a existir.
        wsRef.current.onmessage = null;
        wsRef.current.onopen = null;
        wsRef.current.onerror = null;
        wsRef.current.onclose = null;
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, []);  // array vazio = executa apenas no unmount

  const fetchBrandCategories = async (brandKey: string) => {
    if (brandCategories[brandKey]) return;
    try {
      const data = await ApiClient.request<any>(`/brands/${brandKey}/categories`);
      if (data && data.categories) {
        const flat = data.categories.reduce((acc: any[], group: any) => {
          const items = group.items.map((i: any) => ({ slug: i.path, label: `${group.group} - ${i.label}` }));
          return [...acc, ...items];
        }, []);
        setBrandCategories(prev => ({ ...prev, [brandKey]: flat }));
      }
    } catch (err) {
      console.error(`Erro ao carregar categorias para ${brandKey}:`, err);
    }
  };

  const toggleBrand = (key: string) => {
    setSelectedBrands(prev => {
      const exists = prev.includes(key);
      if (exists) {
        const next = prev.filter(k => k !== key);
        // eslint-disable-next-line @typescript-eslint/no-unused-vars
        const { [key]: _, ...rest } = brandSelections;
        setBrandSelections(rest);
        return next;
      } else {
        fetchBrandCategories(key);
        return [...prev, key];
      }
    });
  };

  const updateBrandSelection = (brandKey: string, categoryPath: string) => {
    setBrandSelections(prev => ({ ...prev, [brandKey]: categoryPath }));
  };

  const startScrape = async () => {
    if (selectedBrands.length === 0) return;

    // Validar se todas as marcas selecionadas têm uma categoria
    const allSelected = selectedBrands.every(bk => brandSelections[bk]);
    if (!allSelected) {
      alert("Por favor, selecione uma categoria para cada marca.");
      return;
    }

    setIsScraping(true);
    setOutputFile(null);
    setLogs([{ type: 'info', text: `Iniciando varredura para: ${selectedBrands.join(', ')}`, time: new Date().toLocaleTimeString() }]);
    setProgress({ current: 0, total: 0, success: 0, error: 0 });

    try {
      const isMulti = selectedBrands.length > 1;
      let payload: any;

      if (isMulti) {
        payload = {
          brands: selectedBrands,
          brand_category_map: brandSelections,
          category_slug: "Varredura Manual"
        };
      } else {
        const brand = selectedBrands[0];
        const selection = brandSelections[brand];
        if (selection.startsWith('http')) {
          payload = { brand, custom_url: selection };
        } else {
          payload = { brand, category_path: selection };
        }
      }

      const res: any = await ApiClient.startScrape(payload, isMulti);
      const jobId = res.job_id;

      const apiUrl = import.meta.env.VITE_API_URL || '';
      const apiKey = import.meta.env.VITE_API_KEY || 'dev-api-key';
      let wsUrl: string;
      if (apiUrl) {
        // Produção (split deploy): converter http(s) → ws(s)
        wsUrl = apiUrl.replace(/^http/, 'ws') + `/ws/${jobId}?api_key=${apiKey}`;
      } else {
        // Dev local (proxy): usar window.location
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        wsUrl = `${protocol}//${window.location.host}/ws/${jobId}?api_key=${apiKey}`;
      }
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onmessage = (e) => {
        let msg: any;
        try {
          msg = JSON.parse(e.data);  // WR-05: frame malformado não derruba o handler nem trava isScraping
        } catch {
          return;
        }
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
                  {brands
                    .filter(b => !['mercado_livre', 'netshoes', 'amazon'].includes(b.brand_key?.toLowerCase()))
                    .map(b => (
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
                <label className="label">Categorias por Marca</label>
                {selectedBrands.length === 0 && <p className="text-muted" style={{ fontSize: '13px' }}>Selecione marcas acima para configurar as categorias.</p>}

                <div className="brand-category-selectors" style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                  {selectedBrands.map(bk => {
                    const brand = brands.find(b => b.brand_key === bk);
                    return (
                      <div key={bk} className="brand-category-item" style={{ background: 'rgba(255,255,255,0.05)', padding: '16px', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.2)' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '12px' }}>
                          <img
                            src={brand?.logo_url || `https://www.google.com/s2/favicons?domain=${brand?.domain}&sz=32`}
                            style={{ width: '20px', height: '20px', borderRadius: '4px' }}
                            alt=""
                          />
                          <span style={{ fontSize: '14px', fontWeight: 600 }}>{brand?.brand_name}</span>
                        </div>
                        <select
                          className="input"
                          style={{ height: '48px', fontSize: '14px', width: '100%', appearance: 'auto' }}
                          value={brandSelections[bk] || ""}
                          onChange={e => updateBrandSelection(bk, e.target.value)}
                        >
                          <option value="">Selecione a categoria...</option>
                          {(brandCategories[bk] || []).map((cat: any, index: number) => (
                            <option key={`${cat.slug}-${index}`} value={cat.slug}>{cat.label}</option>
                          ))}
                        </select>
                      </div>
                    );
                  })}
                </div>
              </div>

              <button
                className="btn btn-primary w-full"
                onClick={startScrape}
                disabled={isScraping || selectedBrands.length === 0}
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

            {outputFile && !isScraping && (
              <motion.div
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                style={{ marginTop: '20px', display: 'flex', justifyContent: 'flex-end' }}
              >
                <a
                  href={`${import.meta.env.VITE_API_URL || ''}/download-report/${outputFile}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="btn btn-success"
                  style={{
                    padding: '12px 24px',
                    fontSize: '1rem',
                    background: '#10b981',
                    color: 'white',
                    boxShadow: '0 4px 15px rgba(16, 185, 129, 0.3)'
                  }}
                >
                  <FileSpreadsheet size={20} />
                  <span style={{ fontWeight: 700 }}>BAIXAR RESULTADOS (EXCEL)</span>
                  <Download size={16} style={{ marginLeft: '8px', opacity: 0.8 }} />
                </a>
              </motion.div>
            )}
          </GlassCard>
        </div>
      </div>
    </div>
  );
};

// --- HistoryList ---

const HistoryList = ({ type, onReopen, refreshKey, collapsed: collapsedProp, onToggleCollapsed, onCountChange }: {
  type: 'search' | 'cross';
  onReopen: (jobId: string) => void;
  refreshKey: number;
  /** Optional controlled collapsed state — when provided (with onToggleCollapsed), an external
   * trigger (e.g. the top-right History icon) drives the panel instead of the internal header button. */
  collapsed?: boolean;
  onToggleCollapsed?: () => void;
  /** Reports the type-filtered item count upward so an external badge can mirror it without a second fetch. */
  onCountChange?: (count: number) => void;
}) => {
  const [items, setItems] = useState<any[]>([]);
  const [collapsedState, setCollapsedState] = useState(true);
  const collapsed = collapsedProp !== undefined ? collapsedProp : collapsedState;
  const setCollapsed = (updater: (c: boolean) => boolean) => {
    if (onToggleCollapsed) { onToggleCollapsed(); return; }
    setCollapsedState(updater);
  };
  const [deleteTick, setDeleteTick] = useState(0);

  useEffect(() => {
    let cancelled = false;
    ApiClient.getHistoryList()
      .then(all => { if (!cancelled) setItems(all.filter((h: any) => h.type === type)); })
      .catch(() => { if (!cancelled) setItems([]); });
    return () => { cancelled = true; };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [refreshKey, deleteTick]);

  useEffect(() => {
    onCountChange?.(items.length);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [items.length]);

  const handleDelete = (e: React.MouseEvent, jobId: string) => {
    e.stopPropagation();
    if (!confirm('Excluir esta busca do histórico? Esta ação é permanente.')) return;
    ApiClient.deleteHistory(jobId)
      .then(() => setDeleteTick(t => t + 1))
      .catch(() => alert('Erro ao excluir entrada do histórico.'));
  };

  const formatDate = (iso: string) => {
    try {
      return new Date(iso).toLocaleString('pt-BR', {
        day: '2-digit', month: '2-digit', year: 'numeric',
        hour: '2-digit', minute: '2-digit',
      });
    } catch {
      return iso;
    }
  };

  const getLabel = (item: any) => {
    if (type === 'cross') return item.query || '';
    const brands: string[] = Array.isArray(item.brands) ? item.brands : [];
    const first2 = brands.slice(0, 2).join(', ');
    const moreSuffix = brands.length > 2 ? ` · ${brands.length} marcas` : '';
    const querySuffix = item.query ? ` — "${item.query}"` : '';
    return `${first2}${moreSuffix}${querySuffix}`;
  };

  const filteredCount = items.length;

  return (
    <div style={{ marginBottom: '16px' }}>
      <div
        style={{
          background: 'rgba(255,255,255,0.04)',
          borderRadius: '12px',
          border: '1px solid rgba(255,255,255,0.08)',
          overflow: 'hidden',
        }}
      >
        {/* Header */}
        <button
          type="button"
          onClick={() => setCollapsed(c => !c)}
          style={{
            width: '100%',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            padding: '12px 16px',
            background: 'transparent',
            border: 'none',
            cursor: 'pointer',
            color: 'var(--text-primary)',
            textAlign: 'left',
          }}
          aria-expanded={!collapsed}
        >
          <History size={16} style={{ color: 'var(--text-muted)', flexShrink: 0 }} />
          <span style={{ fontWeight: 700, fontSize: '0.875rem', flex: 1 }}>Histórico de buscas</span>
          {filteredCount > 0 && (
            <span className="monitor-badge" style={{ color: 'var(--primary)', fontSize: '0.7rem', background: 'rgba(99,102,241,0.12)', padding: '2px 8px', borderRadius: '20px' }}>
              {filteredCount}
            </span>
          )}
          {collapsed
            ? <ChevronRight size={16} style={{ color: 'var(--text-muted)' }} />
            : <ChevronDown size={16} style={{ color: 'var(--text-muted)' }} />
          }
        </button>

        {/* Body */}
        {!collapsed && (
          <div style={{ borderTop: '1px solid rgba(255,255,255,0.06)', padding: '8px 0' }}>
            {items.length === 0 ? (
              <div className="empty-state" style={{ padding: '24px 16px' }}>
                <p style={{ fontWeight: 700, marginBottom: '4px' }}>Nenhuma busca ainda</p>
                <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                  Suas buscas aparecerão aqui automaticamente. Clique em uma entrada concluída para reexibir os resultados sem nova raspagem.
                </p>
              </div>
            ) : (
              <div className="brand-list" style={{ padding: '0 8px', gap: '6px' }}>
                {items.map((item: any) => {
                  const isCompleted = item.status === 'COMPLETED';
                  const isFailed = item.status === 'FAILED';
                  const rowStyle: React.CSSProperties = {
                    cursor: isCompleted ? 'pointer' : 'default',
                    opacity: isFailed ? 0.7 : 1,
                    padding: '10px 12px',
                    borderRadius: '8px',
                    border: '1px solid transparent',
                    background: 'transparent',
                    width: '100%',
                    textAlign: 'left',
                    color: 'inherit',
                    transition: 'background 0.15s, border-color 0.15s',
                  };
                  const inner = (
                    <div className="brand-info" style={{ gap: '10px', flexWrap: 'wrap', alignItems: 'center' }}>
                      <span className="brand-name-text" style={{ flex: 1, minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontSize: '0.875rem' }}>
                        {getLabel(item)}
                      </span>
                      <span className="monitor-badge" style={{
                        color: type === 'search' ? 'var(--primary)' : 'var(--accent, #06b6d4)',
                        background: type === 'search' ? 'rgba(99,102,241,0.12)' : 'rgba(6,182,212,0.12)',
                        padding: '2px 8px', borderRadius: '20px', flexShrink: 0,
                      }}>
                        {type === 'search' ? 'Comparativa' : 'SKU'}
                      </span>
                      <span className="brand-domain-text" style={{ flexShrink: 0 }}>
                        {formatDate(item.created_at)}
                      </span>
                      <span className="monitor-badge" style={{
                        color: isCompleted ? 'var(--success)' : isFailed ? 'var(--error)' : 'var(--warning)',
                        background: isCompleted ? 'rgba(16,185,129,0.12)' : isFailed ? 'rgba(239,68,68,0.12)' : 'rgba(245,158,11,0.12)',
                        padding: '2px 8px', borderRadius: '20px', flexShrink: 0,
                        display: 'flex', alignItems: 'center', gap: '4px',
                      }}>
                        {item.status === 'PENDING' && <RefreshCw className="animate-spin" size={10} />}
                        {isCompleted ? 'Concluída' : isFailed ? 'Falhou' : 'Em andamento'}
                      </span>
                      <button
                        type="button"
                        className="btn-icon text-error"
                        style={{ flexShrink: 0, padding: '4px' }}
                        aria-label="Excluir do histórico"
                        onClick={(e) => handleDelete(e, item.job_id)}
                      >
                        <Trash2 size={15} />
                      </button>
                    </div>
                  );
                  return isCompleted ? (
                    <div
                      key={item.job_id}
                      role="button"
                      tabIndex={0}
                      className="brand-item"
                      style={rowStyle}
                      onClick={() => onReopen(item.job_id)}
                      onKeyDown={e => {
                        if (e.key === 'Enter' || e.key === ' ') {
                          e.preventDefault();
                          onReopen(item.job_id);
                        }
                      }}
                      onMouseEnter={e => {
                        (e.currentTarget as HTMLElement).style.background = 'rgba(99,102,241,0.08)';
                        (e.currentTarget as HTMLElement).style.borderColor = 'rgba(99,102,241,0.25)';
                      }}
                      onMouseLeave={e => {
                        (e.currentTarget as HTMLElement).style.background = 'transparent';
                        (e.currentTarget as HTMLElement).style.borderColor = 'transparent';
                      }}
                      aria-label={`Reabrir busca: ${getLabel(item)}`}
                    >
                      {inner}
                    </div>
                  ) : (
                    <div key={item.job_id} className="brand-item" style={rowStyle}>
                      {inner}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

// --- BannersPage (Phase 34) ---

const ProtectedBannerImage = ({ runId, banner }: { runId: string, banner: BannerCandidate }) => {
  const [src, setSrc] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    let disposed = false;
    let objectUrl: string | null = null;
    ApiClient.getBannerAssetBlob(runId, banner.banner_id).then(blob => {
      if (disposed) return;
      objectUrl = window.URL.createObjectURL(blob);
      setSrc(objectUrl);
    }).catch(() => setFailed(true));
    return () => {
      disposed = true;
      if (objectUrl) window.URL.revokeObjectURL(objectUrl);
    };
  }, [runId, banner.banner_id]);
  if (failed) return <div className="banner-image-loading"><XCircle size={22} /><span>Imagem indisponível</span></div>;
  return src
    ? <img src={src} alt={banner.alt_text || `${banner.brand_name} — banner ${banner.slide_order}`} />
    : <div className="banner-image-loading"><RefreshCw className="animate-spin" size={22} /><span>Carregando imagem…</span></div>;
};

const BannersPage = ({ brands }: { brands: any[] }) => {
  const virtualMarketplaces = new Set(['mercado_livre', 'netshoes', 'amazon']);
  const activeBrands = brands.filter(brand => brand.is_active !== false && !virtualMarketplaces.has(brand.brand_key));
  const {
    selectedBrands, starting, activeJobId, run, selectedBannerIds, history, historyLoading,
    setSelectedBrands, initializeBrands, start, stop, toggleBanner, selectAllBanners,
    clearBanners, approve, loadHistory, reopenHistory, deleteHistory,
  } = useBannerStore(useShallow(state => ({
    selectedBrands: state.selectedBrands,
    starting: state.starting,
    activeJobId: state.activeJobId,
    run: state.run,
    selectedBannerIds: state.selectedBannerIds,
    history: state.history,
    historyLoading: state.historyLoading,
    setSelectedBrands: state.setSelectedBrands,
    initializeBrands: state.initializeBrands,
    start: state.start,
    stop: state.stop,
    toggleBanner: state.toggleBanner,
    selectAllBanners: state.selectAllBanners,
    clearBanners: state.clearBanners,
    approve: state.approve,
    loadHistory: state.loadHistory,
    reopenHistory: state.reopenHistory,
    deleteHistory: state.deleteHistory,
  })));
  const [historyCollapsed, setHistoryCollapsed] = useState(true);

  useEffect(() => {
    initializeBrands(activeBrands.map(brand => brand.brand_key));
  // `brands` is the stable input; `activeBrands` is intentionally derived each render.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [brands, initializeBrands]);
  useEffect(() => { void loadHistory(); }, [loadHistory]);

  const running = run?.status === 'RUNNING';
  const busy = starting || running;
  const reviewable = run?.status === 'REVIEW';
  const progressRows = run ? Object.values(run.brand_progress) : [];
  const processed = progressRows.filter(item => !['PENDING', 'RUNNING'].includes(item.status)).length;
  const percent = progressRows.length ? Math.round((processed / progressRows.length) * 100) : 0;

  const toggleBrand = (key: string) => setSelectedBrands(
    selectedBrands.includes(key) ? selectedBrands.filter(item => item !== key) : [...selectedBrands, key]
  );
  const statusLabel: Record<string, string> = {
    PENDING: 'Aguardando', RUNNING: 'Extraindo', COMPLETED: 'Concluída',
    FAILED: 'Falhou', CANCELLED: 'Cancelada',
  };
  const formatDate = (iso: string) => new Date(iso).toLocaleString('pt-BR', {
    day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit',
  });
  const handleApprove = () => {
    if (!selectedBannerIds.length) return;
    if (confirm(`Aprovar ${selectedBannerIds.length} banners? Os itens desmarcados serão removidos e esta aprovação não poderá ser alterada.`)) {
      void approve();
    }
  };
  const openProtected = (blob: Promise<Blob>) => {
    void ApiClient.openProtectedBlob(blob).catch(error => toast.error(`Erro ao abrir arquivo: ${error.message}`));
  };
  const openAsset = (banner: BannerCandidate) => {
    if (!activeJobId) return;
    openProtected(ApiClient.getBannerAssetBlob(activeJobId, banner.banner_id));
  };
  const openScreenshot = (brandKey: string) => {
    if (!activeJobId) return;
    openProtected(ApiClient.getBannerScreenshotBlob(activeJobId, brandKey));
  };

  return (
    <div className="page-content banners-page">
      <GlassCard title="Extração de banners" subtitle="Selecione as marcas e extraia todos os banners desktop do carrossel principal.">
        <div className="brand-filter-panel">
          <div className="brand-filter-header">
            <div>
              <h3 className="brand-filter-title">Marcas ativas</h3>
              <p className="brand-filter-caption">{selectedBrands.length} de {activeBrands.length} marcas selecionadas</p>
            </div>
            <div className="brand-filter-actions">
              <button type="button" className="btn btn-sm btn-outline" disabled={busy} onClick={() => setSelectedBrands(activeBrands.map(brand => brand.brand_key))}>Selecionar todas</button>
              <button type="button" className="btn btn-sm btn-outline" disabled={busy} onClick={() => setSelectedBrands([])}>Desmarcar todas</button>
            </div>
          </div>
          {activeBrands.length === 0 ? <div className="empty-state">Nenhuma marca ativa disponível</div> : (
            <div className="search-brand-grid brand-selector-grid banner-brand-grid">
              {activeBrands.map(brand => (
                <button type="button" key={brand.brand_key} disabled={busy}
                  className={`brand-chip ${selectedBrands.includes(brand.brand_key) ? 'active' : ''}`}
                  aria-pressed={selectedBrands.includes(brand.brand_key)} onClick={() => toggleBrand(brand.brand_key)}>
                  <div className="brand-chip-icon"><img src={brand.logo_url || `https://www.google.com/s2/favicons?domain=${brand.domain}&sz=64`} alt="" /></div>
                  <span>{brand.brand_name}</span>
                </button>
              ))}
            </div>
          )}
          <div className="banner-primary-action">
            {running ? (
              <button type="button" className="btn btn-stop" onClick={() => void stop()}><Square size={17} fill="currentColor" /> Parar extração</button>
            ) : starting ? (
              <button type="button" className="btn btn-primary" disabled><RefreshCw className="animate-spin" size={18} /> Iniciando…</button>
            ) : (
              <button type="button" className="btn btn-primary" disabled={!selectedBrands.length} onClick={() => void start()}><Images size={18} /> Extrair banners</button>
            )}
          </div>
        </div>
      </GlassCard>

      {run && (
        <GlassCard title={running ? 'Extração em andamento' : 'Resumo da extração'}>
          <div className="banner-progress-heading"><span>{processed} de {progressRows.length} marcas processadas</span><strong>{percent}%</strong></div>
          <div className="progress-bar-large" role="progressbar" aria-label="Progresso da extração" aria-valuemin={0} aria-valuemax={100} aria-valuenow={percent}>
            <div className="progress-fill-large" style={{ width: `${percent}%` }} />
          </div>
          <div className="banner-progress-list">
            {progressRows.map(item => (
              <div className="banner-progress-row" key={item.brand_key}>
                <span>{item.brand_name}</span>
                <span className={`banner-status status-${item.status.toLowerCase()}`}>{statusLabel[item.status] || item.status}</span>
                <span>{item.banner_count} imagem(ns)</span>
                {Boolean(item.screenshot_asset) && <button type="button" className="btn-link" onClick={() => openScreenshot(item.brand_key)}>Ver primeira tela</button>}
                {item.error && <small title={item.error}>{item.error}</small>}
              </div>
            ))}
          </div>
          {run.status === 'CANCELLED' && <div className="status-banner info"><Pause size={18} /><span>Extração interrompida. Resultados parciais não serão salvos no histórico.</span></div>}
          {run.status === 'PARTIAL' && <div className="status-banner error"><AlertTriangle size={18} /><span>Algumas marcas falharam. Os resultados ficam apenas nesta sessão e não entram no histórico.</span></div>}
          {run.status === 'FAILED' && <div className="status-banner error"><XCircle size={18} /><span>{run.error || 'Não foi possível concluir a extração.'}</span></div>}
        </GlassCard>
      )}

      {run && run.banners.length > 0 && activeJobId && (
        <GlassCard title={reviewable ? 'Revisar banners' : run.status === 'COMPLETED' ? 'Banners aprovados' : 'Resultados desta sessão'}>
          <div className="banner-review-toolbar">
            <strong>{selectedBannerIds.length} de {run.banners.length} selecionados</strong>
            {reviewable && <>
              <button type="button" className="btn btn-sm btn-outline" onClick={selectAllBanners}>Selecionar todos</button>
              <button type="button" className="btn btn-sm btn-outline" onClick={clearBanners}>Desmarcar todos</button>
              <button type="button" className="btn btn-primary" disabled={!selectedBannerIds.length} onClick={handleApprove}>Aprovar {selectedBannerIds.length} banners</button>
            </>}
            {run.status === 'COMPLETED' && <div className="banner-report-actions">
              {(['json', 'csv', 'html'] as const).map(format => <button type="button" className="btn btn-sm btn-outline" key={format} onClick={() => openProtected(ApiClient.getBannerReportBlob(run.run_id, format))}>{format.toUpperCase()}</button>)}
            </div>}
          </div>
          {reviewable && !selectedBannerIds.length && <p className="banner-selection-warning">Selecione ao menos um banner para aprovar.</p>}
          <div className="banner-gallery">
            {run.banners.map(banner => {
              const selected = selectedBannerIds.includes(banner.banner_id);
              return (
                <article key={banner.banner_id} className={`banner-card ${selected ? 'selected' : 'unselected'} ${reviewable ? 'reviewable' : ''}`}
                  role={reviewable ? 'checkbox' : undefined} aria-checked={reviewable ? selected : undefined} tabIndex={reviewable ? 0 : undefined}
                  onClick={() => reviewable && toggleBanner(banner.banner_id)}
                  onKeyDown={event => { if (reviewable && (event.key === ' ' || event.key === 'Enter')) { event.preventDefault(); toggleBanner(banner.banner_id); } }}>
                  {reviewable && <span className="banner-card-check">{selected && <Check size={16} />}</span>}
                  <div className="banner-preview"><ProtectedBannerImage runId={run.run_id} banner={banner} /></div>
                  <div className="banner-card-body">
                    <strong>{banner.brand_name}</strong><span>{banner.friendly_filename}</span>
                    <small>{banner.natural_width || banner.rendered_width || '—'}×{banner.natural_height || banner.rendered_height || '—'} px · {banner.asset.extension.toUpperCase()} · slide {banner.slide_order}</small>
                    <button type="button" className="btn-link" onClick={event => { event.stopPropagation(); openAsset(banner); }}><ExternalLink size={14} /> Abrir original</button>
                  </div>
                </article>
              );
            })}
          </div>
        </GlassCard>
      )}

      <section className="banner-history-panel">
        <button type="button" className="banner-history-toggle" aria-expanded={!historyCollapsed} onClick={() => setHistoryCollapsed(value => !value)}>
          <History size={17} /><strong>Histórico de banners</strong><span className="monitor-badge">{history.length}</span>
          {historyCollapsed ? <ChevronRight size={16} /> : <ChevronDown size={16} />}
        </button>
        {!historyCollapsed && <div className="banner-history-list">
          {historyLoading ? <div className="empty-state"><RefreshCw className="animate-spin" size={20} /> Carregando histórico…</div> : history.length === 0 ? (
            <div className="empty-state"><strong>Nenhuma extração aprovada ainda</strong><p>As extrações concluídas e aprovadas aparecerão aqui por 30 dias.</p></div>
          ) : history.map(item => (
            <div role="button" tabIndex={0} className="banner-history-row" key={item.run_id} onClick={() => void reopenHistory(item.run_id)}
              onKeyDown={event => { if (event.key === 'Enter') void reopenHistory(item.run_id); }}>
              <span><strong>{formatDate(item.approved_at)}</strong><small>{item.banner_count} banners · {item.brand_count} marcas</small></span>
              <span className="banner-status status-completed">Concluída</span>
              <span role="button" tabIndex={0} className="btn-icon text-error" aria-label="Excluir extração do histórico"
                onClick={event => { event.stopPropagation(); if (confirm('Excluir esta extração do histórico? Os arquivos sem outras referências também serão removidos.')) void deleteHistory(item.run_id); }}
                onKeyDown={event => { if (event.key === 'Enter') { event.stopPropagation(); if (confirm('Excluir esta extração do histórico?')) void deleteHistory(item.run_id); } }}><Trash2 size={16} /></span>
            </div>
          ))}
        </div>}
      </section>
    </div>
  );
};

// --- SearchPage ---

type SearchPageProps = { brands: any[], preloadedJobId?: string | null, onClearPreloadedJob?: () => void, onReopen?: (jobId: string) => void };
const SearchPage = ({ brands, preloadedJobId, onClearPreloadedJob, onReopen }: SearchPageProps) => {
  // Store selectors — seletores atômicos para campos que disparam renders pesados (Armadilha 1)
  const loading = useSearchStore((s) => s.search.loading);
  const results = useSearchStore((s) => s.search.results);
  // useShallow para múltiplos campos do mesmo slice (evita re-render por referência nova do objeto)
  const { query, sort, inStock, zipcode, selectedBrands } = useSearchStore(
    useShallow((s) => ({
      query: s.search.query,
      sort: s.search.sort,
      inStock: s.search.inStock,
      zipcode: s.search.zipcode,
      selectedBrands: s.search.selectedBrands,
    }))
  );
  // Actions
  const setSearch = useSearchStore((s) => s.setSearch);
  const startSearch = useSearchStore((s) => s.startSearch);
  // UI transiente — permanecem como useState local (D-03)
  const [exporting, setExporting] = useState(false);
  const [historyRefreshKey, setHistoryRefreshKey] = useState(0);
  // --- Histórico de buscas: ícone no topo controla o painel (UX-06) ---
  const [historyOpen, setHistoryOpen] = useState(false);
  const [historyCount, setHistoryCount] = useState(0);
  // --- Campo de CEP da barra de busca (opcional, sem valor padrão) ---
  // Se preenchido antes da busca, o frete de TODOS os produtos vem junto (include_shipping).
  const [cepFieldError, setCepFieldError] = useState<string | null>(null);
  const cepFieldRef = useRef<HTMLInputElement>(null);
  // --- Frete sob demanda (modal de CEP + cálculo de um único produto) ---
  const [cepModalOpen, setCepModalOpen] = useState(false);
  const [cepDraft, setCepDraft] = useState('');
  const [cepError, setCepError] = useState<string | null>(null);
  // pendingCalc: o que calcular assim que o usuário confirmar o CEP no modal.
  const [pendingCalc, setPendingCalc] = useState<
    | { type: 'all' }
    | { type: 'one'; brandKey: string; product: any; key: string }
    | null
  >(null);
  const [loadingShipping, setLoadingShipping] = useState<Record<string, boolean>>({});
  const [expandedShipping, setExpandedShipping] = useState<Record<string, boolean>>({});
  const cepDraftRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (preloadedJobId) {
      const slice = useSearchStore.getState().search;
      // Guarda anti-duplo-fetch (Padrão 3): pula apenas se ESTE mesmo job já está sendo
      // pré-carregado — ex.: remount por troca de aba durante a pré-carga.
      if (slice.loading && slice.loadingPreloadId === preloadedJobId) return;
      // Reabrir do histórico é a intenção explícita mais recente: cancela qualquer
      // busca normal em voo para não correr lado a lado com a pré-carga (WR-03).
      slice.abortController?.abort();
      setSearch({ loading: true, loadingPreloadId: preloadedJobId, abortController: null });
      ApiClient.getHistoryDetail(preloadedJobId).then(res => {
        // Identity guard: uma operação mais nova assumiu o slice — não clobberar.
        if (useSearchStore.getState().search.loadingPreloadId !== preloadedJobId) return;
        setSearch({
          results: { results: res.results, query: res.query, brands_searched: res.brands },
          query: res.query || '',
          loading: false,
          loadingPreloadId: null,
        });
      }).catch(() => {
        if (useSearchStore.getState().search.loadingPreloadId !== preloadedJobId) return;
        toast.error("Erro ao carregar resultados do histórico");
      })
        .finally(() => {
          if (useSearchStore.getState().search.loadingPreloadId === preloadedJobId) {
            setSearch({ loading: false, loadingPreloadId: null });
          }
          if (onClearPreloadedJob) onClearPreloadedJob();
        });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [preloadedJobId]);

  const toggleBrand = (key: string) => {
    const next = selectedBrands.includes(key)
      ? selectedBrands.filter(k => k !== key)
      : [...selectedBrands, key];
    setSearch({ selectedBrands: next });
  };

  const selectAllBrands = () => {
    // Só marcas ativas são alvos válidos de /search (inativas → 400). Espelha BannersPage.
    setSearch({ selectedBrands: brands.filter(b => b.is_active !== false).map(b => b.brand_key) });
  };

  const clearBrands = () => {
    setSearch({ selectedBrands: [] });
  };

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    // CEP é OPCIONAL. Se o usuário preencher um CEP válido ANTES da busca, o frete de
    // todos os produtos vem junto (include_shipping). Sem CEP → busca só preços, e o
    // frete fica sob demanda via "Calcular Frete" por produto.
    const cepDigits = zipcode.replace(/\D/g, '');
    if (cepDigits.length > 0 && cepDigits.length < 8) {
      setCepFieldError('Informe um CEP válido com 8 dígitos.');
      cepFieldRef.current?.focus();
      return;
    }
    setCepFieldError(null);
    onClearPreloadedJob?.();
    const outcome = await startSearch({
      query,
      sort,
      only_in_stock: inStock,
      brands: selectedBrands.length > 0 ? selectedBrands : undefined,
      zipcode: cepDigits.length === 8 ? cepDigits : undefined,
      include_shipping: cepDigits.length === 8 ? true : undefined,
    });
    // historyRefreshKey permanece local (D-03) — só refaz a HistoryList em busca CONCLUÍDA
    // (não em cancelamento/erro — WR-06)
    if (outcome.status === 'success') {
      setHistoryRefreshKey(k => k + 1);
    }
  };

  const handleExport = async () => {
    if (!query) return;
    const cepDigits = zipcode.replace(/\D/g, '');
    if (cepDigits.length > 0 && cepDigits.length < 8) {
      setCepFieldError('Informe um CEP válido com 8 dígitos.');
      cepFieldRef.current?.focus();
      return;
    }
    setCepFieldError(null);
    setExporting(true);
    try {
      await ApiClient.exportSearch({
        query,
        sort,
        only_in_stock: inStock,
        brands: selectedBrands.length > 0 ? selectedBrands : undefined,
        zipcode: cepDigits.length === 8 ? cepDigits : undefined,
        include_shipping: cepDigits.length === 8 ? true : undefined,
      });
    } catch (err: any) {
      console.error(err);
      alert("Erro ao exportar: " + err.message);
    } finally {
      setExporting(false);
    }
  };

  // -------------------------------------------------------------------------
  // Adicionar ao monitoramento
  // -------------------------------------------------------------------------
  const handleAddToMonitor = async (url: string, brand: string) => {
    try {
      const result = await ApiClient.addToMonitor(url, brand);
      if (result.status === 'already_active') {
        toast.info('Produto já está em monitoramento');
      } else if (result.status === 'reactivated') {
        toast.success('Monitor reativado');
      } else {
        toast.success('Adicionado ao monitoramento');
      }
    } catch (err: any) {
      toast.error(err.message || 'Erro ao adicionar ao monitoramento');
    }
  };

  // -------------------------------------------------------------------------
  // Frete sob demanda (modal de CEP + cálculo por produto VTEX)
  // -------------------------------------------------------------------------

  // Achata todos os produtos com frete sob demanda suportado nos resultados atuais.
  const shippingProductsInResults = (): Array<{ brandKey: string; p: any }> => {
    const out: Array<{ brandKey: string; p: any }> = [];
    const rows = results && Array.isArray(results.results) ? results.results : [];
    for (const row of rows) {
      const meta = brands.find(b => b.brand_key === row.brand_key);
      const engine = meta?.engine;
      for (const p of (row.products || [])) {
        if (engine === 'vtex' && p.sku_id) out.push({ brandKey: row.brand_key, p });
        if (engine === 'shopify' || engine === 'wake') out.push({ brandKey: row.brand_key, p });
      }
    }
    return out;
  };

  // Aplica o resultado da simulação de frete a um produto (por url) dentro de search.results.
  const applyShippingToProduct = (productUrl: string, data: { state: string; shipping_options: any[]; shipping?: any; shipping_price?: number | null; is_free_shipping?: boolean }) => {
    const cur = useSearchStore.getState().search.results;
    if (!cur || !Array.isArray(cur.results)) return;
    const newResults = cur.results.map((row: any) => ({
      ...row,
      products: (row.products || []).map((p: any) => {
        if (p.url !== productUrl) return p;
        const opts = data.shipping_options || [];
        const primary = opts.length > 0 ? opts[0] : null;
        return {
          ...p,
          _shipping_state: data.state,
          shipping_options: opts,
          shipping: primary || data.shipping || null,
          shipping_price: primary ? primary.price : (data.shipping_price ?? null),
          is_free_shipping: primary ? primary.is_free_shipping : (data.is_free_shipping ?? false),
        };
      }),
    }));
    setSearch({ results: { ...cur, results: newResults } });
  };

  const runCalcOne = async (brandKey: string, product: any, key: string, zip: string) => {
    setLoadingShipping(prev => ({ ...prev, [key]: true }));
    try {
      const meta = brands.find(b => b.brand_key === brandKey);
      const data = meta?.engine === 'vtex'
        ? await ApiClient.calculateVtexShipping({
          brand_key: brandKey,
          sku_id: product.sku_id,
          seller_id: product.seller_id || '1',
          zipcode: zip,
        })
        : await ApiClient.calculateShippingBrand({
          brand_key: brandKey,
          product_url: product.url,
          zipcode: zip,
        });
      applyShippingToProduct(key, data);
      setExpandedShipping(prev => ({ ...prev, [key]: true }));
    } catch (err: any) {
      toast.error('Erro ao calcular frete: ' + err.message);
    } finally {
      setLoadingShipping(prev => ({ ...prev, [key]: false }));
    }
  };

  const runCalcAll = async (zip: string) => {
    const targets = shippingProductsInResults();
    if (targets.length === 0) {
      toast.info('Nenhum produto com frete suportado para calcular.');
      return;
    }
    await Promise.all(
      targets.map(({ brandKey, p }) =>
        runCalcOne(brandKey, p, p.url, zip)
      )
    );
  };

  // Abre o modal de CEP ou calcula direto se o CEP da sessão já é válido.
  const requestCalc = (calc: { type: 'all' } | { type: 'one'; brandKey: string; product: any; key: string }) => {
    const zip = zipcode.replace(/\D/g, '');
    if (zip.length === 8) {
      if (calc.type === 'one') runCalcOne(calc.brandKey, calc.product, calc.key, zip);
      else runCalcAll(zip);
      return;
    }
    setPendingCalc(calc);
    setCepDraft(zipcode);
    setCepError(null);
    setCepModalOpen(true);
  };

  const confirmCep = () => {
    const zip = cepDraft.replace(/\D/g, '');
    if (zip.length !== 8) {
      setCepError('Informe um CEP válido com 8 dígitos.');
      cepDraftRef.current?.focus();
      return;
    }
    const masked = zip.slice(0, 5) + '-' + zip.slice(5);
    setSearch({ zipcode: masked });
    setCepModalOpen(false);
    setCepError(null);
    const pc = pendingCalc;
    setPendingCalc(null);
    if (pc?.type === 'one') runCalcOne(pc.brandKey, pc.product, pc.key, zip);
    else if (pc?.type === 'all') runCalcAll(zip);
  };

  // Expandir / recolher todos os fretes já calculados.
  const setAllExpanded = (value: boolean) => {
    const next: Record<string, boolean> = {};
    for (const { p } of shippingProductsInResults()) {
      if (p._shipping_state || (Array.isArray(p.shipping_options) && p.shipping_options.length > 0)) {
        next[p.url] = value;
      }
    }
    setExpandedShipping(next);
  };

  return (
    <div className="page-content">
      <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
        <button
          type="button"
          className="btn-icon"
          title="Ver histórico de buscas"
          onClick={() => setHistoryOpen(o => !o)}
          style={{ position: 'relative' }}
        >
          <History size={18} />
          {historyCount > 0 && (
            <span
              className="monitor-badge"
              style={{
                position: 'absolute', top: '-6px', right: '-6px',
                color: 'var(--primary)', fontSize: '0.65rem',
                background: 'rgba(99,102,241,0.12)', padding: '2px 6px', borderRadius: '20px',
              }}
            >
              {historyCount}
            </span>
          )}
        </button>
      </div>
      {onReopen && (
        <HistoryList
          type="search"
          onReopen={onReopen}
          refreshKey={historyRefreshKey}
          collapsed={!historyOpen}
          onToggleCollapsed={() => setHistoryOpen(o => !o)}
          onCountChange={setHistoryCount}
        />
      )}
      <GlassCard className="search-bar-container">
        <form onSubmit={handleSearch} className="search-form">
          <div className="search-main-row">
            <div className="search-field">
              <label className="search-field-label">O que você procura?</label>
              <div className="search-input-wrapper">
                <Search className="search-icon" size={20} />
                <input
                  type="text"
                  className="search-input"
                  placeholder="Ex: Polo Piquet, Camisa Social..."
                  value={query}
                  onChange={(e) => setSearch({ query: e.target.value })}
                />
              </div>
            </div>

            <div className="search-field">
              <label className="search-field-label" htmlFor="cep-input">CEP de entrega (opcional)</label>
              <div className={`search-input-wrapper${cepFieldError ? ' cep-input-error' : ''}`}>
                <MapPin className="search-icon" size={20} aria-hidden="true" />
                <input
                  id="cep-input"
                  ref={cepFieldRef}
                  type="text"
                  inputMode="numeric"
                  autoComplete="postal-code"
                  className="search-input"
                  placeholder="00000-000"
                  value={zipcode}
                  aria-invalid={cepFieldError ? 'true' : 'false'}
                  aria-describedby={cepFieldError ? 'cep-error-msg' : 'cep-helper-msg'}
                  onChange={(e) => {
                    let val = e.target.value.replace(/\D/g, '');
                    if (val.length > 8) val = val.slice(0, 8);
                    if (val.length > 5) {
                      val = val.slice(0, 5) + '-' + val.slice(5);
                    }
                    setSearch({ zipcode: val });
                    if (cepFieldError) setCepFieldError(null);
                  }}
                />
              </div>
              {cepFieldError ? (
                <p id="cep-error-msg" className="cep-helper cep-helper-error" role="alert" aria-live="polite">
                  <AlertTriangle size={12} aria-hidden="true" />
                  {cepFieldError}
                </p>
              ) : (
                <p id="cep-helper-msg" className="cep-helper">
                  Informe para calcular o frete junto da busca. Sem CEP, calcule por produto.
                </p>
              )}
            </div>
          </div>

          <div className="search-control-row">
            <div className="search-field">
              <label className="search-field-label">Ordenação</label>
              <select className="input" value={sort} onChange={e => setSearch({ sort: e.target.value })}>
                <option value="relevance">Relevância</option>
                <option value="recent">Mais Recentes</option>
                <option value="price_asc">Menor Preço</option>
                <option value="price_desc">Maior Preço</option>
                <option value="top_selling">Mais Vendidos</option>
              </select>
            </div>

            <label className={`stock-toggle ${inStock ? 'active' : ''}`}>
              <input type="checkbox" checked={inStock} onChange={e => setSearch({ inStock: e.target.checked })} />
              <div className="stock-toggle-box">
                {inStock && <CheckCircle2 size={12} />}
              </div>
              Apenas em estoque
            </label>

            <div className="search-actions">
              <button type="submit" className="btn btn-primary search-submit" disabled={loading || exporting}>
                {loading ? <RefreshCw className="animate-spin" size={18} /> : "Comparar"}
              </button>
              <button
                type="button"
                className="btn btn-outline btn-excel"
                onClick={handleExport}
                disabled={loading || exporting || !query}
                title="Exportar Busca para Excel"
              >
                {exporting ? <RefreshCw className="animate-spin" size={18} /> : <FileSpreadsheet size={18} />}
                <span style={{ fontSize: '14px', marginLeft: '4px' }}>Excel</span>
              </button>
            </div>
          </div>
        </form>

        <div className="divider" style={{ margin: '16px 0', opacity: 0.2 }} />

        <div className="brand-filter-panel">
          <div className="brand-filter-header">
            <div>
              <h3 className="brand-filter-title" style={{ fontSize: '0.95rem', fontWeight: 700 }}>Filtro de Marcas</h3>
              <p className="brand-filter-caption">
                {selectedBrands.length === 0 ? 'Buscando em todas as marcas ativas no sistema' : `${selectedBrands.length} marca(s) selecionada(s)`}
              </p>
            </div>
            <div className="brand-filter-actions">
              <button type="button" className="btn btn-sm btn-outline" onClick={selectAllBrands} style={{ padding: '6px 12px', fontSize: '12px', minHeight: 'unset', border: '1px solid rgba(255,255,255,0.2)' }}>Selecionar Todas</button>
              <button type="button" className="btn btn-sm btn-outline" onClick={clearBrands} style={{ padding: '6px 12px', fontSize: '12px', minHeight: 'unset', border: '1px solid rgba(255,255,255,0.2)' }}>Limpar Seleção</button>
            </div>
          </div>

          <div className="search-brand-grid brand-selector-grid" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(150px, 1fr))' }}>
            {brands.filter(b => b.is_active !== false).map(b => (
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
        {results && (() => {
          // When no brand filter: use brand keys from actual results (includes Amazon, ML, NS)
          const brandKeysToShow = selectedBrands.length > 0
            ? selectedBrands
            : (Array.isArray(results.results) ? results.results.map((r: any) => r.brand_key) : brands.map(b => b.brand_key));

          const shippingProds = shippingProductsInResults();
          const anyCalculated = shippingProds.some(({ p }) =>
            p._shipping_state || (Array.isArray(p.shipping_options) && p.shipping_options.length > 0) || p.shipping
          );

          return (
            <>
              {/* Barra de controle: calcular frete de todos + expandir/recolher (só quando há produtos VTEX) */}
              {shippingProds.length > 0 && (
                <div className="shipping-controls-bar">
                  <button
                    type="button"
                    className="btn btn-sm btn-outline"
                    onClick={() => requestCalc({ type: 'all' })}
                  >
                    <Truck size={14} aria-hidden="true" /> Calcular frete de todos
                  </button>
                  {anyCalculated && (
                    <>
                      <button type="button" className="btn btn-sm btn-outline" onClick={() => setAllExpanded(true)}>Expandir todos</button>
                      <button type="button" className="btn btn-sm btn-outline" onClick={() => setAllExpanded(false)}>Recolher todos</button>
                    </>
                  )}
                </div>
              )}

              {brandKeysToShow.map((brandKey: string) => {
            const brand = brands.find(b => b.brand_key === brandKey);
            const brandRes = Array.isArray(results.results) ? results.results.find((r: any) => r.brand_key === brandKey) : null;
            const products = brandRes?.products || [];
            const isVtex = brand?.engine === 'vtex';
            const isBrandShippingSupported = brand?.engine === 'shopify' || brand?.engine === 'wake';

            return (
              <div key={brandKey} className="brand-column">
                <h4 className="brand-header">{brand?.brand_name || brandKey}</h4>
                <div className="product-grid">
                  {products.map((p: any) => (
                    <a
                      key={p.url}
                      href={p.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="product-card"
                    >
                      <div className="product-image">
                        {p.image_url ? <img src={p.image_url} alt={p.product_name} /> : <Package size={40} />}
                        {p.price_discount > 0 && <span className="badge-discount">{Math.round((p.price_discount / (p.price_full + p.price_discount)) * 100)}% OFF</span>}
                      </div>
                      <div className="product-details">
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '8px' }}>
                          <p className="product-name">{p.product_name}</p>
                          <ExternalLink size={14} className="text-muted" style={{ marginTop: '4px', flexShrink: 0 }} />
                        </div>
                        <div className="product-price" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          {p.price_discount > 0 && (
                            <span className="price-original" style={{ textDecoration: 'line-through', color: '#999', fontSize: '0.85em' }}>
                              R$ {(p.price_full + p.price_discount).toFixed(2)}
                            </span>
                          )}
                          <span className="price-current">R$ {(p.price_full ?? 0).toFixed(2)}</span>
                        </div>
                        <div className="product-meta">
                          {p.available ? <CheckCircle2 size={14} className="text-success" /> : <XCircle size={14} className="text-error" />}
                          <span>{p.available ? 'Em estoque' : 'Esgotado'}</span>
                        </div>
                        {/* Frete: botão sob demanda (sem CEP/cálculo) OU resumo colapsável (já calculado).
                            Detalhe fica colapsado por padrão para não poluir o card. */}
                        {(() => {
                          const opts = Array.isArray(p.shipping_options) ? p.shipping_options : null;
                          const hasOptions = !!opts && opts.length > 0;
                          const isLoading = !!loadingShipping[p.url];
                          const isExpanded = !!expandedShipping[p.url];
                          const calculated = !!p._shipping_state || hasOptions || !!p.shipping;

                          // Estado de loading
                          if (isLoading) {
                            return (
                              <div className="shipping-section">
                                <div className="shipping-loading">
                                  <RefreshCw size={13} className="animate-spin" aria-hidden="true" /> Calculando frete…
                                </div>
                              </div>
                            );
                          }

                          // Ainda não calculado → botão sob demanda (VTEX com sku apenas)
                          if (!calculated) {
                            if (!(isBrandShippingSupported || (isVtex && p.sku_id))) return null;
                            return (
                              <div className="shipping-section">
                                <button
                                  type="button"
                                  className="shipping-calc-btn"
                                  onClick={(e) => {
                                    e.preventDefault();
                                    e.stopPropagation();
                                    requestCalc({ type: 'one', brandKey, product: p, key: p.url });
                                  }}
                                >
                                  <Truck size={14} aria-hidden="true" /> Calcular Frete
                                </button>
                              </div>
                            );
                          }

                          // Calculado, com opções de entrega → resumo colapsável
                          if (hasOptions) {
                            const cheapest = opts[0];
                            const cheapestFree = cheapest.is_free_shipping === true || cheapest.price === 0 || cheapest.price === 0.0;
                            const summary = cheapestFree
                              ? 'Frete Grátis'
                              : `Frete a partir de R$ ${(cheapest.price ?? 0).toFixed(2).replace('.', ',')}`;
                            return (
                              <div className="shipping-section">
                                <button
                                  type="button"
                                  className="shipping-summary"
                                  aria-expanded={isExpanded}
                                  onClick={(e) => {
                                    e.preventDefault();
                                    e.stopPropagation();
                                    setExpandedShipping(prev => ({ ...prev, [p.url]: !prev[p.url] }));
                                  }}
                                >
                                  <span className="shipping-summary-main">
                                    <Truck size={14} aria-hidden="true" />
                                    <span className={cheapestFree ? 'shipping-free' : undefined}>{summary}</span>
                                  </span>
                                  {isExpanded ? <ChevronUp size={14} aria-hidden="true" /> : <ChevronDown size={14} aria-hidden="true" />}
                                </button>
                                {isExpanded && (
                                  <ul className="shipping-options-list">
                                    {/* Backend order: price asc then estimate asc — do NOT re-sort (D-10) */}
                                    {opts.map((opt: any, idx: number) => {
                                      const isFree = opt.is_free_shipping === true || opt.price === 0 || opt.price === 0.0;
                                      const serviceName = opt.service_name || opt.service_id || 'Entrega';
                                      const estimateText = opt.estimate_display || opt.raw_text || (opt.estimated_delivery_days ? `Até ${opt.estimated_delivery_days} dias úteis` : '');
                                      return (
                                        <li key={idx} className="shipping-option-row">
                                          <div className="shipping-option-service">
                                            <span className="shipping-service-name">{serviceName}</span>
                                            {estimateText && <span className="shipping-estimate">{estimateText}</span>}
                                          </div>
                                          <div className="shipping-option-price">
                                            {isFree ? (
                                              <span className="shipping-free">
                                                <CheckCircle2 size={12} aria-hidden="true" />
                                                Frete Grátis
                                              </span>
                                            ) : (
                                              <span className="shipping-paid">
                                                R$ {(opt.price ?? 0).toFixed(2).replace('.', ',')}
                                              </span>
                                            )}
                                          </div>
                                        </li>
                                      );
                                    })}
                                  </ul>
                                )}
                              </div>
                            );
                          }

                          // Calculado sem opções → estado indisponível / falha temporária
                          const statusLower = (p.shipping?.status || '').toLowerCase();
                          const isFailure = p._shipping_state === 'temporary_failure' || statusLower.includes('temporariamente');
                          const isUnavailable = p._shipping_state === 'unavailable_for_cep' || statusLower.includes('indisponível');
                          if (isFailure || isUnavailable) {
                            const stateText = isFailure
                              ? 'Frete temporariamente indisponível'
                              : 'Entrega indisponível para este CEP';
                            return (
                              <div className="shipping-section">
                                <div className={`shipping-state-row ${isFailure ? 'shipping-state-warning' : 'shipping-state-unavailable'}`}>
                                  {isFailure ? <AlertTriangle size={13} aria-hidden="true" /> : <MapPin size={13} aria-hidden="true" />}
                                  <span>{stateText}</span>
                                  {isFailure && (isBrandShippingSupported || (isVtex && p.sku_id)) && (
                                    <button
                                      type="button"
                                      className="shipping-retry"
                                      onClick={(e) => {
                                        e.preventDefault();
                                        e.stopPropagation();
                                        requestCalc({ type: 'one', brandKey, product: p, key: p.url });
                                      }}
                                    >
                                      Tentar novamente
                                    </button>
                                  )}
                                </div>
                              </div>
                            );
                          }

                          // Fallback legado: registros antigos com p.shipping simples (D-08 compat)
                          if (p.shipping) {
                            return (
                              <div className="product-meta" style={{ marginTop: '6px', color: p.shipping.status === 'Grátis' ? 'var(--success)' : 'inherit' }}>
                                <Package size={14} aria-hidden="true" />
                                <span>
                                  {p.shipping.status === 'Grátis' ? 'Frete Grátis' : (p.shipping.price ? `Frete: R$ ${p.shipping.price.toFixed(2)}` : p.shipping.status)}
                                  {p.shipping.estimated_delivery_days ? ` (${p.shipping.estimated_delivery_days} dias)` : ''}
                                </span>
                              </div>
                            );
                          }

                          return null;
                        })()}
                      </div>
                      <div style={{ marginTop: '8px', display: 'flex', justifyContent: 'flex-end' }}>
                        <button
                          type="button"
                          className="btn-icon btn-sm"
                          title="Adicionar ao monitoramento"
                          onClick={async (e) => {
                            e.preventDefault();
                            e.stopPropagation();
                            await handleAddToMonitor(p.url, brandKey);
                          }}
                        >
                          <Plus size={14} />
                        </button>
                      </div>
                    </a>
                  ))}
                  {products.length === 0 && (
                    <div className="empty-column" style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-muted)', background: 'rgba(255,255,255,0.02)', borderRadius: '12px', border: '1px dashed var(--border)' }}>
                      <p style={{ fontSize: '0.9rem' }}>Nenhum resultado encontrado</p>
                    </div>
                  )}
                </div>
              </div>
            );
              })}
            </>
          );
        })()}
      </div>

      {/* Modal de CEP — pede o CEP quando o usuário calcula frete sem ter informado um */}
      {cepModalOpen && (
        <div className="modal-overlay" onClick={() => setCepModalOpen(false)}>
          <div className="modal-content" onClick={e => e.stopPropagation()} style={{ maxWidth: '420px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <h3 style={{ margin: 0, display: 'flex', alignItems: 'center', gap: '8px' }}>
                <MapPin size={18} /> Calcular frete
              </h3>
              <button className="btn btn-icon" onClick={() => setCepModalOpen(false)} aria-label="Fechar"><X size={20} /></button>
            </div>
            <p className="text-muted" style={{ marginBottom: '12px', fontSize: '13px' }}>
              Informe o CEP de entrega para calcular o frete.
            </p>
            <div className={`search-input-wrapper${cepError ? ' cep-input-error' : ''}`}>
              <MapPin className="search-icon" size={20} aria-hidden="true" />
              <input
                ref={cepDraftRef}
                type="text"
                inputMode="numeric"
                autoComplete="postal-code"
                className="search-input"
                placeholder="00000-000"
                value={cepDraft}
                autoFocus
                aria-invalid={cepError ? 'true' : 'false'}
                onChange={(e) => {
                  let val = e.target.value.replace(/\D/g, '');
                  if (val.length > 8) val = val.slice(0, 8);
                  if (val.length > 5) val = val.slice(0, 5) + '-' + val.slice(5);
                  setCepDraft(val);
                  if (cepError) setCepError(null);
                }}
                onKeyDown={(e) => { if (e.key === 'Enter') confirmCep(); }}
              />
            </div>
            {cepError && (
              <p className="cep-helper cep-helper-error" role="alert" aria-live="polite" style={{ marginTop: '8px' }}>
                <AlertTriangle size={12} aria-hidden="true" /> {cepError}
              </p>
            )}
            <div style={{ display: 'flex', gap: '12px', marginTop: '16px' }}>
              <button type="button" className="btn btn-outline" onClick={() => setCepModalOpen(false)} style={{ flex: 1 }}>Cancelar</button>
              <button type="button" className="btn btn-primary" onClick={confirmCep} style={{ flex: 1 }}>Calcular</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

type CrossMarketplacePageProps = { preloadedJobId?: string | null, onClearPreloadedJob?: () => void, onReopen?: (jobId: string) => void };
const CrossMarketplacePage = ({ preloadedJobId, onClearPreloadedJob, onReopen }: CrossMarketplacePageProps) => {
  // Store selectors — seletores atômicos para campos que disparam renders pesados (Armadilha 1)
  const loading = useSearchStore((s) => s.cross.loading);
  const results = useSearchStore((s) => s.cross.results);
  const selectedItems = useSearchStore((s) => s.cross.selectedItems);
  const selectionMode = useSearchStore((s) => s.cross.selectionMode);
  // useShallow para múltiplos campos do mesmo slice
  const { targetSku, zipcode } = useSearchStore(
    useShallow((s) => ({
      targetSku: s.cross.targetSku,
      zipcode: s.cross.zipcode,
    }))
  );
  // Actions
  const setCross = useSearchStore((s) => s.setCross);
  const startCrossSearch = useSearchStore((s) => s.startCrossSearch);
  // UI transiente — permanecem como useState local (D-03)
  const [loadingShipping, setLoadingShipping] = useState<Record<string, boolean>>({});
  const [exporting, setExporting] = useState(false);
  const [historyRefreshKey, setHistoryRefreshKey] = useState(0);
  // --- Histórico de buscas: ícone no topo controla o painel (UX-06) ---
  const [historyOpen, setHistoryOpen] = useState(false);
  const [historyCount, setHistoryCount] = useState(0);
  // Modal de CEP — mesma lógica da busca comparativa: ao clicar "Calcular Frete" sem CEP,
  // abre o modal em vez de bloquear com alert.
  const [cepModalOpen, setCepModalOpen] = useState(false);
  const [cepDraft, setCepDraft] = useState('');
  const [cepError, setCepError] = useState<string | null>(null);
  const [pendingShipItem, setPendingShipItem] = useState<{ item: any; marketplace: string } | null>(null);
  const cepDraftRef = useRef<HTMLInputElement>(null);

  // withDisplayOrder importado do store (fonte única — CR-01/IN-02): a action
  // startCrossSearch e a pré-carga de histórico aplicam exatamente a mesma lógica.
  const allItems: any[] = results?.results ?? [];

  const toggleItem = (url: string) => {
    const next = new Set(selectedItems);
    if (next.has(url)) {
      next.delete(url);
    } else {
      next.add(url);
    }
    setCross({ selectedItems: next });
  };

  const isAllSelected = allItems.length > 0 && allItems.every((i: any) => selectedItems.has(i.url));

  const toggleSelectAll = () => {
    if (isAllSelected) {
      setCross({ selectedItems: new Set() });
    } else {
      setCross({ selectedItems: new Set(allItems.map((i: any) => i.url)) });
    }
  };

  // Marketplace brand_key lookup map (D-07 / Pitfall 6)
  const MARKETPLACE_BRAND_KEY: Record<string, string> = {
    'Mercado Livre': 'mercado_livre',
    'Netshoes': 'netshoes',
    'Amazon': 'amazon',
  };

  const handleAddToMonitor = async (url: string, brand: string) => {
    try {
      const result = await ApiClient.addToMonitor(url, brand);
      if (result.status === 'already_active') {
        toast.info('Produto já está em monitoramento');
      } else if (result.status === 'reactivated') {
        toast.success('Monitor reativado');
      } else {
        toast.success('Adicionado ao monitoramento');
      }
    } catch (err: any) {
      toast.error(err.message || 'Erro ao adicionar ao monitoramento');
    }
  };

  const handleExport = async (mode: 'all' | 'selected') => {
    const itemsToExport = mode === 'all'
      ? allItems
      : allItems.filter((i: any) => selectedItems.has(i.url));
    setExporting(true);
    try {
      await ApiClient.exportCrossMarketplace({
        items: itemsToExport,
        search_query: results?.search_query,
        target_sku: targetSku,
      });
    } catch (err: any) {
      toast.error('Erro ao exportar: ' + err.message);
    } finally {
      setExporting(false);
      setCross({ selectionMode: false, selectedItems: new Set() });
    }
  };

  useEffect(() => {
    if (preloadedJobId) {
      const slice = useSearchStore.getState().cross;
      // Guarda anti-duplo-fetch (Padrão 3): pula apenas se ESTE mesmo job já está sendo
      // pré-carregado — ex.: remount por troca de aba durante a pré-carga.
      if (slice.loading && slice.loadingPreloadId === preloadedJobId) return;
      // Reabrir do histórico é a intenção explícita mais recente: cancela qualquer
      // busca por SKU em voo para não correr lado a lado com a pré-carga (WR-03).
      slice.abortController?.abort();
      setCross({ loading: true, loadingPreloadId: preloadedJobId, abortController: null });
      ApiClient.getHistoryDetail(preloadedJobId).then(res => {
        // Identity guard: uma operação mais nova assumiu o slice — não clobberar.
        if (useSearchStore.getState().cross.loadingPreloadId !== preloadedJobId) return;
        setCross({
          results: withDisplayOrder(res.results),
          targetSku: res.query ? res.query.replace('SKU: ', '') : '',
          selectionMode: false,
          selectedItems: new Set(),
          loading: false,
          loadingPreloadId: null,
        });
      }).catch(() => {
        if (useSearchStore.getState().cross.loadingPreloadId !== preloadedJobId) return;
        toast.error("Erro ao carregar resultados do histórico");
      })
        .finally(() => {
          if (useSearchStore.getState().cross.loadingPreloadId === preloadedJobId) {
            setCross({ loading: false, loadingPreloadId: null });
          }
          if (onClearPreloadedJob) onClearPreloadedJob();
        });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [preloadedJobId]);

  // Núcleo do cálculo de frete de UM item (já com CEP validado).
  const runShipForItem = async (item: any, marketplace: string, currentZip: string) => {
    const key = `${marketplace}-${item.url}`;
    setLoadingShipping(prev => ({ ...prev, [key]: true }));
    // Snapshot do result set ANTES do await: se uma nova busca por SKU ou reabertura de
    // histórico substituir os resultados durante o cálculo, não splicear o frete no
    // conjunto de OUTRA busca (mesma classe de race do CR-01 — WR-01).
    const baseResults = useSearchStore.getState().cross.results;

    try {
      const data = await ApiClient.calculateSingleShipping({
        marketplace,
        url: item.url,
        zipcode: currentZip
      });

      if (data.status === 'success' && data.shipping_info) {
        // Lê o estado atual do store (equivalente ao prev do useState funcional)
        const prev = useSearchStore.getState().cross.results;
        // Staleness guard (WR-01): result set trocado durante o await → descarta a escrita.
        if (!prev || prev !== baseResults) return;
        const newResults = prev.results.map((r: any) => {
          if (r.url === item.url && r.marketplace === marketplace) {
            const newShippingPrice = data.shipping_info.shipping_price;
            const isFree = data.shipping_info.is_free_shipping;
            return {
              ...r,
              is_free_shipping: isFree,
              shipping_price: newShippingPrice,
              landed_price: r.price + (newShippingPrice || 0)
            };
          }
          return r;
        });

        // Reavalia o is_buybox_winner com os novos preços landed
        const minPrice = Math.min(...newResults.map((r: any) => r.landed_price ?? r.price));
        newResults.forEach((r: any) => {
          r.is_buybox_winner = (r.landed_price ?? r.price) === minPrice;
        });

        setCross({ results: { ...prev, results: newResults } });
      } else {
        toast.error(data.message || "Erro ao calcular frete");
      }
    } catch (err: any) {
      toast.error("Erro ao calcular frete: " + err.message);
    } finally {
      setLoadingShipping(prev => ({ ...prev, [key]: false }));
    }
  };

  // Entry handler do botão "Calcular Frete": usa o CEP da sessão se válido, senão abre o modal.
  const handleCalculateShipping = (e: React.MouseEvent, item: any, marketplace: string) => {
    e.preventDefault();
    e.stopPropagation();
    const currentZip = zipcode.replace(/\D/g, '');
    if (currentZip.length === 8) {
      runShipForItem(item, marketplace, currentZip);
      return;
    }
    setPendingShipItem({ item, marketplace });
    setCepDraft(zipcode);
    setCepError(null);
    setCepModalOpen(true);
  };

  const confirmCepCross = () => {
    const zip = cepDraft.replace(/\D/g, '');
    if (zip.length !== 8) {
      setCepError('Informe um CEP válido com 8 dígitos.');
      cepDraftRef.current?.focus();
      return;
    }
    const masked = zip.slice(0, 5) + '-' + zip.slice(5);
    setCross({ zipcode: masked });
    setCepModalOpen(false);
    setCepError(null);
    const pending = pendingShipItem;
    setPendingShipItem(null);
    if (pending) runShipForItem(pending.item, pending.marketplace, zip);
  };

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!targetSku) return;
    onClearPreloadedJob?.();
    // startCrossSearch faz: loading=true, results=null, reset seleção, AbortController,
    // withDisplayOrder e toast — tudo dentro da action (CR-01).
    const outcome = await startCrossSearch({
      target_sku: targetSku,
      zipcode: zipcode.replace(/\D/g, '').length === 8 ? zipcode.replace(/\D/g, '') : undefined,
    });
    // CR-01: withDisplayOrder já é aplicado dentro de startCrossSearch (fonte única) —
    // não reescrever o store após o await (evita re-wrap de resultados de outra busca).
    // historyRefreshKey permanece local (D-03) — só refaz a HistoryList em busca CONCLUÍDA,
    // não em cancelamento/erro (WR-06).
    if (outcome.status === 'success') {
      setHistoryRefreshKey(k => k + 1);
    }
  };

  return (
    <div className="page-content">
      <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
        <button
          type="button"
          className="btn-icon"
          title="Ver histórico de buscas"
          onClick={() => setHistoryOpen(o => !o)}
          style={{ position: 'relative' }}
        >
          <History size={18} />
          {historyCount > 0 && (
            <span
              className="monitor-badge"
              style={{
                position: 'absolute', top: '-6px', right: '-6px',
                color: 'var(--primary)', fontSize: '0.65rem',
                background: 'rgba(99,102,241,0.12)', padding: '2px 6px', borderRadius: '20px',
              }}
            >
              {historyCount}
            </span>
          )}
        </button>
      </div>
      {onReopen && (
        <HistoryList
          type="cross"
          onReopen={onReopen}
          refreshKey={historyRefreshKey}
          collapsed={!historyOpen}
          onToggleCollapsed={() => setHistoryOpen(o => !o)}
          onCountChange={setHistoryCount}
        />
      )}
      <GlassCard className="search-bar-container">
        <form onSubmit={handleSearch} className="form-stack">
          <div className="form-group" style={{ display: 'flex', gap: '16px' }}>
            <div style={{ flex: 1 }}>
              <label className="label">SKU Alvo (Aramis)</label>
              <input
                type="text"
                className="input"
                placeholder="Ex: ML.05.0326046"
                value={targetSku}
                onChange={e => setCross({ targetSku: e.target.value })}
                required
              />
            </div>
            <div style={{ width: '200px' }}>
              <label className="label">CEP (Opcional)</label>
              <input
                type="text"
                className="input"
                placeholder="Ex: 01001-000"
                value={zipcode}
                onChange={e => {
                  let val = e.target.value.replace(/\D/g, '');
                  if (val.length > 8) val = val.slice(0, 8);
                  if (val.length > 5) val = val.slice(0, 5) + '-' + val.slice(5);
                  setCross({ zipcode: val });
                }}
              />
            </div>
          </div>
          <p className="text-muted mt-2" style={{ fontSize: '12px', marginTop: '8px' }}>
            Ao informar o SKU, o sistema irá automaticamente na loja da Aramis identificar o nome e categoria do produto para varrer os demais marketplaces.
          </p>
          <button type="submit" className="btn btn-primary w-full" disabled={loading}>
            {loading ? <RefreshCw className="animate-spin" size={18} /> : <Radar size={18} />}
            {loading ? "Rastreando Concorrência..." : "Buscar em Marketplaces"}
          </button>
        </form>
      </GlassCard>

      {results && (
        <div style={{ marginTop: '24px', display: 'flex', flexDirection: 'column', gap: '24px' }}>


          {results.reference_product && (
            <GlassCard title="Produto Referência (Aramis)">
              <div style={{ display: 'flex', gap: '16px', alignItems: 'center' }}>
                {results.reference_product.image_url ? (
                  <img
                    src={results.reference_product.image_url}
                    alt={results.reference_product.name}
                    style={{ width: '80px', height: '80px', objectFit: 'contain', borderRadius: '8px', background: 'white' }}
                  />
                ) : (
                  <div style={{ width: '80px', height: '80px', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'rgba(255,255,255,0.1)', borderRadius: '8px' }}>
                    <Package size={32} className="text-muted" />
                  </div>
                )}
                <div>
                  <h3 style={{ margin: '0 0 8px 0', fontSize: '16px' }}>{results.reference_product.name}</h3>
                  <p style={{ margin: 0, fontSize: '14px', color: '#10b981', fontWeight: 'bold' }}>R$ {results.reference_product.price.toFixed(2)}</p>
                  <a href={results.reference_product.url} target="_blank" rel="noopener noreferrer" style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', fontSize: '12px', color: '#6366f1', marginTop: '8px', textDecoration: 'none' }}>
                    Ver no site <ExternalLink size={12} />
                  </a>
                </div>
              </div>
            </GlassCard>
          )}

          {results.errors && results.errors.length > 0 && (
            <GlassCard>
              <h3 style={{ color: '#ef4444', marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '8px', fontSize: '16px' }}>
                <AlertTriangle size={18} /> Marketplaces com Falha
              </h3>
              <ul style={{ listStyle: 'none', padding: 0, margin: 0, fontSize: '14px', color: 'var(--text-muted)' }}>
                {results.errors.map((err: any, i: number) => (
                  <li key={i} style={{ marginBottom: '8px' }}>
                    <strong style={{ color: '#fff' }}>{err.marketplace}:</strong> {err.reason}
                  </li>
                ))}
              </ul>
            </GlassCard>
          )}

          {/* Export toolbar */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '16px', marginBottom: '16px' }}>
            {selectionMode ? (
              <>
                <label className={`stock-toggle${isAllSelected ? ' active' : ''}`} style={{ cursor: 'pointer' }}>
                  <input type="checkbox" checked={isAllSelected} onChange={toggleSelectAll} />
                  <span className="stock-toggle-box">
                    {isAllSelected && <Check size={12} />}
                  </span>
                  Selecionar todos
                </label>
                <span className={`sku-export-counter${selectedItems.size > 0 ? ' has-selection' : ''}`}>
                  {selectedItems.size} selecionado(s)
                </span>
                <div style={{ flex: 1 }} />
                <button
                  className="btn btn-primary"
                  onClick={() => handleExport('all')}
                  disabled={exporting}
                >
                  {exporting ? <><RefreshCw size={16} className="animate-spin" /> Exportando...</> : <><FileSpreadsheet size={16} /> Exportar todos</>}
                </button>
                <button
                  className="btn btn-excel"
                  onClick={() => handleExport('selected')}
                  disabled={exporting || selectedItems.size === 0}
                  style={selectedItems.size === 0 ? { opacity: 0.4, cursor: 'not-allowed' } : undefined}
                >
                  {exporting ? <><RefreshCw size={16} className="animate-spin" /> Exportando...</> : <><FileSpreadsheet size={16} /> Exportar selecionados ({selectedItems.size})</>}
                </button>
                <button
                  className="btn"
                  onClick={() => { setCross({ selectionMode: false, selectedItems: new Set() }); }}
                  disabled={exporting}
                >
                  Cancelar
                </button>
              </>
            ) : (
              <>
                <div style={{ flex: 1 }} />
                <button
                  className="btn btn-excel"
                  onClick={() => setCross({ selectionMode: true })}
                  disabled={exporting}
                >
                  {exporting
                    ? <><RefreshCw size={16} className="animate-spin" /> Exportando...</>
                    : <><FileSpreadsheet size={16} /> Exportar Excel</>
                  }
                </button>
              </>
            )}
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '16px', marginTop: '16px' }}>
            {['Mercado Livre', 'Netshoes', 'Amazon'].map(marketplace => {
              const marketResults = (results.results || [])
                .map((r: any, index: number) => ({ ...r, _render_order: r._display_order ?? index }))
                .filter((r: any) => r.marketplace === marketplace);

              marketResults.sort((a: any, b: any) => {
                return a._render_order - b._render_order;
              });

              return (
                <GlassCard key={marketplace} title={marketplace}>
                  {marketResults.length > 0 ? (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', marginTop: '16px' }}>
                      {marketResults.map((item: any, i: number) => (
                        <a
                          key={`${marketplace}-${item.url || i}`}
                          href={item.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          style={{
                            position: 'relative',
                            display: 'flex',
                            flexDirection: 'column',
                            gap: '8px',
                            padding: '12px',
                            background: selectionMode && selectedItems.has(item.url)
                              ? 'rgba(16,185,129,0.07)'
                              : item.is_buybox_winner ? 'rgba(16, 185, 129, 0.1)' : 'rgba(255,255,255,0.02)',
                            border: `1px solid ${selectionMode && selectedItems.has(item.url)
                              ? 'rgba(16,185,129,0.25)'
                              : item.is_buybox_winner ? 'rgba(16, 185, 129, 0.3)' : 'rgba(255,255,255,0.1)'}`,
                            borderRadius: '12px',
                            textDecoration: 'none',
                            color: 'inherit',
                            transition: 'transform 0.2s, background 0.2s'
                          }}
                        >
                          {selectionMode && (
                            <label
                              className="card-select-checkbox"
                              onClick={e => { e.preventDefault(); e.stopPropagation(); toggleItem(item.url); }}
                            >
                              <input
                                type="checkbox"
                                checked={selectedItems.has(item.url)}
                                readOnly
                                tabIndex={-1}
                              />
                              <span className="stock-toggle-box">
                                {selectedItems.has(item.url) && <Check size={12} />}
                              </span>
                            </label>
                          )}
                          <div>
                            <p style={{ margin: '0 0 4px 0', fontSize: '13px', fontWeight: 500, lineHeight: '1.4' }}>
                              {item.is_similar && (
                                <span
                                  title="Produto similar (não é o match exato da marca buscada)"
                                  style={{ fontSize: '9px', fontWeight: 700, textTransform: 'uppercase', color: '#f59e0b', background: 'rgba(245, 158, 11, 0.12)', padding: '1px 6px', borderRadius: '4px', marginRight: '6px', verticalAlign: 'middle' }}
                                >
                                  Similar
                                </span>
                              )}
                              {item.title}
                            </p>
                            <p style={{ margin: 0, fontSize: '11px', color: 'var(--text-muted)' }}>Vendedor: {item.seller}</p>
                          </div>
                          {item.image_url && (
                            <div style={{ width: '100%', height: '140px', overflow: 'hidden', borderRadius: '8px', margin: '4px 0' }}>
                              <img src={item.image_url} alt={item.title} style={{ width: '100%', height: '100%', objectFit: 'contain', backgroundColor: 'transparent' }} />
                            </div>
                          )}
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <span style={{ fontSize: '20px', fontWeight: 'bold', color: item.is_buybox_winner ? '#10b981' : '#fff' }}>
                              R$ {(item.landed_price ?? item.price).toFixed(2)}
                              {item.shipping_price === null && !item.is_free_shipping && (
                                <span title="Frete a calcular" style={{ fontSize: '14px', marginLeft: '6px', verticalAlign: 'top' }}>⚠️</span>
                              )}
                            </span>
                            {item.is_free_shipping ? (
                              <span style={{ fontSize: '10px', color: '#fff', background: '#10b981', padding: '2px 6px', borderRadius: '4px', fontWeight: 'bold' }}>
                                Frete Grátis
                              </span>
                            ) : item.is_buybox_winner ? (
                              <span style={{ fontSize: '10px', color: '#10b981', display: 'flex', alignItems: 'center', gap: '4px', background: 'rgba(16, 185, 129, 0.1)', padding: '2px 6px', borderRadius: '4px' }}>
                                <CheckCircle2 size={10} /> Menor Preço
                              </span>
                            ) : null}
                          </div>
                          <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '2px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                            {item.shipping_price === null && !item.is_free_shipping ? (
                              <>
                                <span style={{ color: '#fbbf24' }}>Frete a calcular</span>
                                <button
                                  onClick={(e) => handleCalculateShipping(e, item, marketplace)}
                                  disabled={loadingShipping[`${marketplace}-${item.url}`]}
                                  style={{
                                    background: 'rgba(251, 191, 36, 0.1)',
                                    border: '1px solid rgba(251, 191, 36, 0.3)',
                                    color: '#fbbf24',
                                    fontSize: '10px',
                                    padding: '3px 8px',
                                    borderRadius: '4px',
                                    cursor: loadingShipping[`${marketplace}-${item.url}`] ? 'not-allowed' : 'pointer',
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '6px',
                                    opacity: loadingShipping[`${marketplace}-${item.url}`] ? 0.7 : 1
                                  }}
                                >
                                  {loadingShipping[`${marketplace}-${item.url}`] ? <RefreshCw size={10} className="animate-spin" /> : <Package size={10} />}
                                  {loadingShipping[`${marketplace}-${item.url}`] ? "Calculando..." : "Calcular Frete"}
                                </button>
                              </>
                            ) : (
                              <span>R$ {item.price.toFixed(2)} (Produto) + R$ {(item.shipping_price || 0).toFixed(2)} (Frete)</span>
                            )}
                          </div>
                          <div style={{ marginTop: '8px', display: 'flex', justifyContent: 'flex-end' }}>
                            <button
                              type="button"
                              className="btn-icon btn-sm"
                              title="Adicionar ao monitoramento"
                              onClick={async (e) => {
                                e.preventDefault();
                                e.stopPropagation();
                                const brandKey = MARKETPLACE_BRAND_KEY[marketplace] || marketplace.toLowerCase().replace(/\s+/g, '_');
                                await handleAddToMonitor(item.url, brandKey);
                              }}
                            >
                              <Plus size={14} />
                            </button>
                          </div>
                        </a>
                      ))}
                    </div>
                  ) : (
                    <div className="empty-state" style={{ marginTop: '16px', padding: '20px' }}>
                      <p style={{ fontSize: '12px' }}>Nenhum produto atendeu ao critério estrito de busca.</p>
                    </div>
                  )}
                </GlassCard>
              )
            })}
          </div>

        </div>
      )}

      {/* Modal de CEP — pede o CEP ao calcular frete sem ter informado um (mesma lógica da comparativa) */}
      {cepModalOpen && (
        <div className="modal-overlay" onClick={() => setCepModalOpen(false)}>
          <div className="modal-content" onClick={e => e.stopPropagation()} style={{ maxWidth: '420px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <h3 style={{ margin: 0, display: 'flex', alignItems: 'center', gap: '8px' }}>
                <MapPin size={18} /> Calcular frete
              </h3>
              <button className="btn btn-icon" onClick={() => setCepModalOpen(false)} aria-label="Fechar"><X size={20} /></button>
            </div>
            <p className="text-muted" style={{ marginBottom: '12px', fontSize: '13px' }}>
              Informe o CEP de entrega para calcular o frete.
            </p>
            <div className={`search-input-wrapper${cepError ? ' cep-input-error' : ''}`}>
              <MapPin className="search-icon" size={20} aria-hidden="true" />
              <input
                ref={cepDraftRef}
                type="text"
                inputMode="numeric"
                autoComplete="postal-code"
                className="search-input"
                placeholder="00000-000"
                value={cepDraft}
                autoFocus
                aria-invalid={cepError ? 'true' : 'false'}
                onChange={(e) => {
                  let val = e.target.value.replace(/\D/g, '');
                  if (val.length > 8) val = val.slice(0, 8);
                  if (val.length > 5) val = val.slice(0, 5) + '-' + val.slice(5);
                  setCepDraft(val);
                  if (cepError) setCepError(null);
                }}
                onKeyDown={(e) => { if (e.key === 'Enter') confirmCepCross(); }}
              />
            </div>
            {cepError && (
              <p className="cep-helper cep-helper-error" role="alert" aria-live="polite" style={{ marginTop: '8px' }}>
                <AlertTriangle size={12} aria-hidden="true" /> {cepError}
              </p>
            )}
            <div style={{ display: 'flex', gap: '12px', marginTop: '16px' }}>
              <button type="button" className="btn btn-outline" onClick={() => setCepModalOpen(false)} style={{ flex: 1 }}>Cancelar</button>
              <button type="button" className="btn btn-primary" onClick={confirmCepCross} style={{ flex: 1 }}>Calcular</button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
};

const SettingsPage = ({ brands, onRefresh }: { brands: any[], onRefresh: () => void }) => {
  const handleDeleteBrand = async (key: string) => {
    if (!confirm(`Tem certeza que deseja excluir a marca ${key}?`)) return;
    try {
      await ApiClient.deleteBrand(key);
      onRefresh();
    } catch (err: any) {
      alert("Erro ao excluir: " + err.message);
    }
  };

  const handleToggleActive = async (brand: any) => {
    try {
      await ApiClient.setBrandActive(brand.brand_key, !brand.is_active);
      onRefresh();
    } catch (err: any) {
      toast.error(`Erro ao ${brand.is_active ? 'desativar' : 'ativar'} marca: ${err.message}`);
    }
  };

  return (
    <div className="page-content">
        <GlassCard title="Gerenciar Marcas">
          <div className="brand-list">
            {brands.map(b => {
              return (
                <div key={b.brand_key} className="brand-item">
                  <div className="brand-info" style={b.is_active === false ? { opacity: 0.55 } : undefined}>
                    <div className="brand-avatar">
                      <img
                        src={b.logo_url || `https://www.google.com/s2/favicons?domain=${b.domain}&sz=64`}
                        alt={b.brand_name}
                        onError={(e: any) => { e.target.src = `https://ui-avatars.com/api/?name=${b.brand_name}&background=6366f1&color=fff`; }}
                      />
                    </div>
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <p className="brand-name-text">{b.brand_name}</p>
                        {b.is_active === false && (
                          <span className="monitor-badge" style={{ color: 'var(--warning)', fontSize: '0.7rem' }}>Inativa</span>
                        )}
                      </div>
                      <p className="brand-domain-text"><Globe size={12} /> {b.domain}</p>
                    </div>
                  </div>
                  <div className="brand-actions">
                    <button
                      type="button"
                      className="btn-icon"
                      style={{ color: b.is_active !== false ? 'var(--primary)' : 'var(--text-muted)' }}
                      onClick={() => handleToggleActive(b)}
                      aria-label={`${b.is_active !== false ? 'Desativar' : 'Ativar'} marca ${b.brand_name}`}
                      aria-pressed={b.is_active !== false}
                    >
                      <Power size={18} />
                    </button>
                    <button
                      type="button"
                      className="btn-icon text-error"
                      onClick={() => handleDeleteBrand(b.brand_key)}
                    >
                      <Trash2 size={18} />
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </GlassCard>
    </div>
  );
};

const stockDepthStateLabel = (state?: string | null) => {
  const labels: Record<string, string> = {
    estimated: 'estimado',
    unavailable: 'indisponivel',
    unsupported: 'nao suportado',
    blocked: 'bloqueado',
    temporary_failure: 'falha temporaria',
  };
  return state ? (labels[state] || state) : '';
};

const reviewsStateLabel = (state?: string | null) => {
  const labels: Record<string, string> = {
    available: 'disponivel',
    unsupported: 'nao suportado',
    temporary_failure: 'falha temporaria',
  };
  return state ? (labels[state] || state) : '';
};

const productReviewComments = (product: any) => {
  if (Array.isArray(product.comments)) return product.comments;
  if (Array.isArray(product.review_comments)) return product.review_comments;
  return [];
};

const reviewCommentDisplayText = (comment: any) => {
  return (
    comment.title ||
    comment.text ||
    [comment.author, comment.created_at].filter(Boolean).join(' - ') ||
    'Avaliacao sem texto'
  );
};

const MonitoredCategoriesPage = ({ brands }: { brands: any[] }) => {
  const [categories, setCategories] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [newCategory, setNewCategory] = useState({ url: '', brand: brands.length > 0 ? brands[0].brand_key : '' });
  const [submitting, setSubmitting] = useState(false);
  const [brandCategories, setBrandCategories] = useState<any[]>([]);
  const [loadingCategories, setLoadingCategories] = useState(false);
  const [manualMode, setManualMode] = useState(false);

  // Products modal
  const [selectedMonitor, setSelectedMonitor] = useState<any | null>(null);
  const [monitorProducts, setMonitorProducts] = useState<any[]>([]);
  const [loadingProducts, setLoadingProducts] = useState(false);
  const [selectedMonitorStockSummary, setSelectedMonitorStockSummary] = useState<any | null>(null);
  const [stockDepthLoadingIds, setStockDepthLoadingIds] = useState<Set<string>>(new Set());
  const [reviewLoadingIds, setReviewLoadingIds] = useState<Set<string>>(new Set());

  const fetchCategories = async () => {
    setLoading(true);
    try {
      const data = await ApiClient.getMonitoredCategories();
      setCategories(data);
    } catch (err: any) {
      alert("Erro ao buscar categorias monitoradas: " + err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    let active = true;
    ApiClient.getMonitoredCategories()
      .then(data => {
        if (active) setCategories(data);
      })
      .catch((err: Error) => {
        if (active) alert("Erro ao buscar categorias monitoradas: " + err.message);
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (!newCategory.brand || !isModalOpen) return;
    let isMounted = true;

    const fetchTree = async () => {
      setLoadingCategories(true);
      try {
        const res = await ApiClient.request<any>(`/brands/${newCategory.brand}/discover`);
        if (isMounted) {
          const cats = res || [];
          setBrandCategories(cats);
          if (cats.length > 0 && !manualMode) {
            // The API returns { name: string, path: string } (where path is the URL)
            setNewCategory(prev => ({ ...prev, url: cats[0].path || cats[0].url }));
          }
        }
      } catch (e) {
        console.error("Failed to load categories", e);
        if (isMounted) {
          setBrandCategories([]);
          setManualMode(true); // Fallback to manual if failed
        }
      } finally {
        if (isMounted) setLoadingCategories(false);
      }
    };

    fetchTree();
    return () => { isMounted = false; };
  }, [newCategory.brand, isModalOpen, manualMode]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      await ApiClient.createMonitoredCategory(newCategory);
      setNewCategory({ url: '', brand: brands.length > 0 ? brands[0].brand_key : '' });
      setIsModalOpen(false);
      fetchCategories();
    } catch (err: any) {
      alert("Erro ao adicionar: " + err.message);
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (monitorId: string) => {
    if (!window.confirm("Deseja realmente excluir este monitoramento?")) return;
    try {
      await ApiClient.deleteMonitoredCategory(monitorId);
      fetchCategories();
    } catch (err: any) {
      alert("Erro ao excluir: " + err.message);
    }
  };

  const handleViewProducts = async (monitor: any) => {
    setSelectedMonitor(monitor);
    setLoadingProducts(true);
    setSelectedMonitorStockSummary(null);
    try {
      const prods = await ApiClient.getMonitoredCategoryProducts(monitor.id);
      setMonitorProducts(prods);
      try {
        const summary = await ApiClient.getMonitoredCategoryStockSummary(monitor.id);
        setSelectedMonitorStockSummary(summary);
      } catch (summaryErr: any) {
        setSelectedMonitorStockSummary(null);
        const message = summaryErr?.message || '';
        if (!message.includes('404') && !message.includes('Resumo de estoque')) {
          toast.error('Erro ao buscar resumo de estoque');
        }
      }
    } catch (err: any) {
      alert("Erro ao buscar produtos: " + err.message);
      setMonitorProducts([]);
      setSelectedMonitorStockSummary(null);
    } finally {
      setLoadingProducts(false);
    }
  };

  const mergeMonitorProductResult = (scanProductId: string, fields: any) => {
    setMonitorProducts(prev => prev.map(product => (
      product.scan_product_id === scanProductId
        ? { ...product, ...fields }
        : product
    )));
  };

  const handleRequestStockDepth = async (product: any) => {
    const scanProductId = product?.scan_product_id;
    if (!selectedMonitor?.id || !scanProductId) return;
    setStockDepthLoadingIds(prev => new Set(prev).add(scanProductId));
    try {
      const result = await ApiClient.requestMonitoredProductStockDepth(selectedMonitor.id, scanProductId);
      mergeMonitorProductResult(scanProductId, result);
      if (result.stock_depth_state === 'estimated') {
        toast.success('Profundidade de estoque atualizada');
      } else {
        toast.info(`Profundidade: ${stockDepthStateLabel(result.stock_depth_state)}`);
      }
    } catch (err: any) {
      toast.error(err.message || 'Erro ao consultar profundidade de estoque');
    } finally {
      setStockDepthLoadingIds(prev => {
        const next = new Set(prev);
        next.delete(scanProductId);
        return next;
      });
    }
  };

  const handleRequestReviewComments = async (product: any) => {
    const scanProductId = product?.scan_product_id;
    if (!selectedMonitor?.id || !scanProductId) return;
    setReviewLoadingIds(prev => new Set(prev).add(scanProductId));
    try {
      const result = await ApiClient.requestMonitoredProductReviews(selectedMonitor.id, scanProductId);
      mergeMonitorProductResult(scanProductId, result);
      if (result.reviews_state === 'available' && result.comments.length > 0) {
        toast.success('Comentarios de avaliacao atualizados');
      } else {
        toast.info(`Avaliacoes: ${reviewsStateLabel(result.reviews_state)}`);
      }
    } catch (err: any) {
      toast.error(err.message || 'Erro ao buscar comentários de avaliação');
    } finally {
      setReviewLoadingIds(prev => {
        const next = new Set(prev);
        next.delete(scanProductId);
        return next;
      });
    }
  };

  const handleAddToMonitor = async (url: string, brand: string) => {
    try {
      const result = await ApiClient.addToMonitor(url, brand);
      if (result.status === 'already_active') {
        toast.info('Produto já está em monitoramento');
      } else if (result.status === 'reactivated') {
        toast.success('Monitor reativado');
      } else {
        toast.success('Adicionado ao monitoramento');
      }
    } catch (err: any) {
      toast.error(err.message || 'Erro ao adicionar ao monitoramento');
    }
  };

  return (
    <div className="page-content">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <h2 style={{ fontSize: '1.2rem', margin: 0 }}>Categorias em Monitoramento</h2>
        <button className="btn btn-primary" onClick={() => {
          setNewCategory(prev => prev.brand || brands.length === 0
            ? prev
            : { ...prev, brand: brands[0].brand_key });
          setIsModalOpen(true);
        }}>
          <Plus size={18} /> Novo Monitor
        </button>
      </div>

      <GlassCard>
        {loading ? (
          <div style={{ padding: '2rem', textAlign: 'center' }}><RefreshCw className="animate-spin" /></div>
        ) : categories.length === 0 ? (
          <div className="empty-state" style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-muted)' }}>
            Nenhuma categoria monitorada no momento.
          </div>
        ) : (
          <div className="table-responsive">
            <table className="modern-table">
              <thead>
                <tr>
                  <th>Marca</th>
                  <th>URL</th>
                  <th>Status</th>
                  <th>Última Varredura</th>
                  <th>Ações</th>
                </tr>
              </thead>
              <tbody>
                {categories.map((c, i) => (
                  <tr key={i}>
                    <td>
                      <span className="badge" style={{ background: 'rgba(99, 102, 241, 0.1)', color: '#818cf8', padding: '4px 8px', borderRadius: '4px', fontSize: '12px' }}>
                        {brands.find(b => b.brand_key === c.brand)?.brand_name || c.brand}
                      </span>
                    </td>
                    <td style={{ maxWidth: '300px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <a href={c.url} target="_blank" rel="noopener noreferrer" style={{ color: '#60a5fa', textDecoration: 'none', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', flex: 1 }}>{c.url}</a>
                        <a href={c.url} target="_blank" rel="noopener noreferrer" style={{ color: '#60a5fa', flexShrink: 0 }} title="Abrir no navegador">
                          <ExternalLink size={14} />
                        </a>
                      </div>
                    </td>
                    <td>
                      {c.status === 'active' ? (
                        <span className="text-success" style={{ display: 'flex', alignItems: 'center', gap: '4px' }}><CheckCircle2 size={14} /> Ativo</span>
                      ) : (
                        <span className="text-error">Inativo</span>
                      )}
                    </td>
                    <td className="text-muted">
                      {c.last_scraped_at ? new Date(c.last_scraped_at).toLocaleString() : 'Nunca'}
                    </td>
                    <td>
                      <div style={{ display: 'flex', gap: '8px' }}>
                        <button className="btn btn-icon btn-outline" onClick={() => handleViewProducts(c)} title="Ver Produtos">
                          <Eye size={16} />
                        </button>
                        <button className="btn btn-icon btn-outline text-error" onClick={() => handleDelete(c.id)} title="Excluir Monitor">
                          <Trash2 size={16} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </GlassCard>

      {isModalOpen && (
        <div className="modal-overlay" onClick={() => setIsModalOpen(false)}>
          <div className="modal-content" onClick={e => e.stopPropagation()}>
            <h3 style={{ marginTop: 0, marginBottom: '16px' }}>Adicionar Categoria</h3>
            <form onSubmit={handleSubmit} className="form-stack">
              <div className="form-group">
                <label className="label">Marca</label>
                <select
                  className="input"
                  value={newCategory.brand}
                  onChange={e => setNewCategory({ ...newCategory, brand: e.target.value })}
                >
                  {brands.map(b => (
                    <option key={b.brand_key} value={b.brand_key}>{b.brand_name}</option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
                  <label className="label">Categoria</label>
                  <button
                    type="button"
                    onClick={() => setManualMode(!manualMode)}
                    style={{ background: 'none', border: 'none', color: '#60a5fa', fontSize: '12px', cursor: 'pointer', textDecoration: 'underline' }}
                  >
                    {manualMode ? 'Selecionar da Lista' : 'Inserir Manualmente'}
                  </button>
                </div>

                {manualMode ? (
                  <input
                    type="url"
                    className="input"
                    placeholder="https://..."
                    value={newCategory.url}
                    onChange={e => setNewCategory({ ...newCategory, url: e.target.value })}
                    required
                  />
                ) : (
                  loadingCategories ? (
                    <div style={{ padding: '8px', color: 'var(--text-muted)', fontSize: '13px', display: 'flex', alignItems: 'center', gap: '8px', background: 'rgba(255,255,255,0.05)', borderRadius: '4px' }}>
                      <RefreshCw className="animate-spin" size={14} /> Carregando árvore de categorias...
                    </div>
                  ) : brandCategories.length === 0 ? (
                    <div style={{ padding: '8px', color: '#fbbf24', fontSize: '13px', background: 'rgba(251, 191, 36, 0.1)', borderRadius: '4px' }}>
                      Nenhuma categoria mapeada. <span style={{ textDecoration: 'underline', cursor: 'pointer' }} onClick={() => setManualMode(true)}>Insira manualmente.</span>
                    </div>
                  ) : (
                    <select
                      className="input"
                      value={newCategory.url}
                      onChange={e => setNewCategory({ ...newCategory, url: e.target.value })}
                      required
                    >
                      {brandCategories.map((c: any, i: number) => (
                        <option key={i} value={c.path || c.url}>{c.name}</option>
                      ))}
                    </select>
                  )
                )}
              </div>
              <div style={{ display: 'flex', gap: '12px', marginTop: '8px' }}>
                <button type="button" className="btn btn-outline" onClick={() => setIsModalOpen(false)} style={{ flex: 1 }}>Cancelar</button>
                <button type="submit" className="btn btn-primary" disabled={submitting} style={{ flex: 1 }}>
                  {submitting ? <RefreshCw className="animate-spin" size={18} /> : 'Salvar'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {selectedMonitor && (
        <div className="modal-overlay" onClick={() => setSelectedMonitor(null)}>
          <div className="modal-content" onClick={e => e.stopPropagation()} style={{ maxWidth: '1200px', width: '95%' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <h3 style={{ margin: 0 }}>Produtos em Monitoramento</h3>
              <button className="btn btn-icon" onClick={() => setSelectedMonitor(null)}><X size={20} /></button>
            </div>
            <p className="text-muted" style={{ marginBottom: '16px' }}>
              <span className="badge" style={{ background: 'rgba(99, 102, 241, 0.1)', color: '#818cf8', marginRight: '8px' }}>{selectedMonitor.brand}</span>
              {selectedMonitor.url}
            </p>
            {selectedMonitorStockSummary && (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: '8px', marginBottom: '16px' }}>
                <div className="badge" style={{ justifyContent: 'space-between', padding: '8px', background: 'rgba(16, 185, 129, 0.1)', color: 'var(--success)' }}>
                  <span>Verificados</span>
                  <strong>{selectedMonitorStockSummary.verified_stock_count}</strong>
                </div>
                <div className="badge" style={{ justifyContent: 'space-between', padding: '8px', background: 'rgba(148, 163, 184, 0.12)', color: 'var(--text-muted)' }}>
                  <span>Nao verificados</span>
                  <strong>{selectedMonitorStockSummary.unknown_stock_count}</strong>
                </div>
                <div className="badge" style={{ justifyContent: 'space-between', padding: '8px', background: 'rgba(239, 68, 68, 0.1)', color: 'var(--error)' }}>
                  <span>Esgotados</span>
                  <strong>{selectedMonitorStockSummary.out_of_stock_count}</strong>
                </div>
                {selectedMonitorStockSummary.rupture_pct !== null && (
                  <div className="badge" style={{ justifyContent: 'space-between', padding: '8px', background: 'rgba(245, 158, 11, 0.12)', color: 'var(--warning)' }}>
                    <span>Ruptura</span>
                    <strong>{Math.round(selectedMonitorStockSummary.rupture_pct * 100)}%</strong>
                  </div>
                )}
              </div>
            )}

            {loadingProducts ? (
              <div style={{ padding: '2rem', textAlign: 'center' }}><RefreshCw className="animate-spin" /></div>
            ) : monitorProducts.length === 0 ? (
              <div className="empty-state" style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-muted)' }}>
                Nenhum produto extraído ainda. Aguarde a próxima varredura.
              </div>
            ) : (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(250px, 1fr))', gap: '24px', maxHeight: '600px', overflowY: 'auto', padding: '4px' }}>
                {monitorProducts.map((p, i) => (
                  <a
                    key={i}
                    href={p.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="product-card"
                    onClick={e => { if (!p.url) e.preventDefault(); }}
                  >
                    <div className="product-image">
                      {p.image_url ? (
                        <img src={p.image_url} alt={p.name} />
                      ) : (
                        <Package size={40} />
                      )}
                      {p.price_discount && p.price_discount > 0 ? (
                        <span className="badge-discount">-{Math.round((p.price_discount / (p.price_full + p.price_discount)) * 100)}%</span>
                      ) : null}
                    </div>
                    <div className="product-details">
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '8px' }}>
                        <p className="product-name" title={p.raw_title}>{p.raw_title || 'Produto sem título'}</p>
                        {p.url && <ExternalLink size={14} className="text-muted" style={{ marginTop: '4px', flexShrink: 0 }} />}
                      </div>
                      <div className="product-price" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        {p.price_discount && p.price_discount > 0 ? (
                          <>
                            <span className="price-original" style={{ textDecoration: 'line-through', color: '#999', fontSize: '0.85em' }}>
                              R$ {(p.price_full + p.price_discount).toFixed(2)}
                            </span>
                            <span className="price-current">R$ {p.price_full?.toFixed(2)}</span>
                          </>
                        ) : (
                          <span className="price-current">R$ {p.price_full?.toFixed(2) || '0.00'}</span>
                        )}
                      </div>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', marginTop: '8px', fontSize: '12px', color: 'var(--text-muted)' }}>
                        {p.stock_availability === true && <span className="text-success">Em estoque</span>}
                        {p.stock_availability === false && <span className="text-error">Esgotado</span>}
                        {p.stock_availability == null && <span>Estoque nao verificado</span>}
                        {p.stock_depth_state && (
                          <span>
                            Profundidade: {p.stock_depth_estimate ?? '-'} ({stockDepthStateLabel(p.stock_depth_state)})
                          </span>
                        )}
                        {p.reviews_state && (
                          <span>
                            Avaliacoes: {p.review_count ?? 0} ({reviewsStateLabel(p.reviews_state)})
                          </span>
                        )}
                        {productReviewComments(p).length > 0 && (
                          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', marginTop: '4px' }}>
                            {productReviewComments(p).slice(0, 2).map((comment: any) => (
                              <span key={comment.review_id} title={reviewCommentDisplayText(comment)}>
                                {comment.rating ? `${comment.rating}/5 - ` : ''}{reviewCommentDisplayText(comment)}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                    {(p.url || p.scan_product_id) && (
                      <div style={{ marginTop: '8px', display: 'flex', justifyContent: 'flex-end', gap: '8px' }}>
                        {p.scan_product_id && (
                          <>
                            <button
                              type="button"
                              className="btn-icon btn-sm"
                              title="Consultar profundidade de estoque"
                              disabled={stockDepthLoadingIds.has(p.scan_product_id)}
                              onClick={async (e) => {
                                e.preventDefault();
                                e.stopPropagation();
                                await handleRequestStockDepth(p);
                              }}
                            >
                              {stockDepthLoadingIds.has(p.scan_product_id) ? <RefreshCw className="animate-spin" size={14} /> : <Gauge size={14} />}
                            </button>
                            <button
                              type="button"
                              className="btn-icon btn-sm"
                              title="Buscar comentários de avaliação"
                              disabled={reviewLoadingIds.has(p.scan_product_id)}
                              onClick={async (e) => {
                                e.preventDefault();
                                e.stopPropagation();
                                await handleRequestReviewComments(p);
                              }}
                            >
                              {reviewLoadingIds.has(p.scan_product_id) ? <RefreshCw className="animate-spin" size={14} /> : <MessageSquare size={14} />}
                            </button>
                          </>
                        )}
                        {p.url && (
                        <button
                          type="button"
                          className="btn-icon btn-sm"
                          title="Adicionar ao monitoramento"
                          onClick={async (e) => {
                            e.preventDefault();
                            e.stopPropagation();
                            await handleAddToMonitor(p.url, selectedMonitor.brand);
                          }}
                        >
                          <Plus size={14} />
                        </button>
                        )}
                      </div>
                    )}
                  </a>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};



// --- Main App ---

function App() {
  const [activeTab, setActiveTab] = useState('monitor');
  const [brands, setBrands] = useState<any[]>([]);
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const [isMobileSidebarOpen, setIsMobileSidebarOpen] = useState(false);
  const [preloadedJobId, setPreloadedJobId] = useState<string | null>(null);

  const handleReopen = (jobId: string, type: 'search' | 'cross') => {
    setActiveTab(type === 'cross' ? 'cross' : 'search');
    setPreloadedJobId(jobId);
  };

  // Manual tab navigation must clear any pending reopen so a stale history job
  // (possibly of the other search type) is never handed to the destination page.
  const navigateTab = (tab: string) => {
    setPreloadedJobId(null);
    setActiveTab(tab);
    setIsMobileSidebarOpen(false);
  };

  const refreshBrands = () => {
    ApiClient.getBrands().then(data => {
      if (Array.isArray(data)) setBrands(data);
    }).catch(err => console.error('Erro ao carregar marcas:', err));
  };

  useEffect(() => {
    refreshBrands();
  }, []);

  const renderTab = () => {
    switch (activeTab) {
      case 'monitor': return <MonitorPage brands={brands} />;
      case 'search': return <SearchPage brands={brands} preloadedJobId={preloadedJobId} onClearPreloadedJob={() => setPreloadedJobId(null)} onReopen={(jobId) => handleReopen(jobId, 'search')} />;
      case 'cross': return <CrossMarketplacePage preloadedJobId={preloadedJobId} onClearPreloadedJob={() => setPreloadedJobId(null)} onReopen={(jobId) => handleReopen(jobId, 'cross')} />;
      case 'monitored_categories': return <MonitoredCategoriesPage brands={brands} />;
      case 'category': return <CategoryPage brands={brands} />;
      case 'banners': return <BannersPage brands={brands} />;
      case 'settings': return <SettingsPage brands={brands} onRefresh={refreshBrands} />;
      default: return <div className="p-8">Selecione uma aba...</div>;
    }
  };

  return (
    <div className="app-container">
      {isMobileSidebarOpen && (
        <div className="mobile-overlay" onClick={() => setIsMobileSidebarOpen(false)} />
      )}
      <aside className={`sidebar ${isSidebarCollapsed ? 'collapsed' : ''} ${isMobileSidebarOpen ? 'mobile-open' : ''}`}>
        <button
          className="sidebar-toggle-btn hidden-on-mobile absolute-toggle-btn"
          onClick={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
        >
          {isSidebarCollapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
        </button>
        <div className="sidebar-header">
          <div className="logo-icon"><Zap size={24} fill="white" /></div>
          <h2>E-Scraper</h2>
        </div>
        <nav className="sidebar-nav">
          <SidebarItem
            icon={LayoutDashboard}
            label="Monitores"
            active={activeTab === 'monitor'}
            onClick={() => navigateTab('monitor')}
          />
          <SidebarItem
            icon={CheckCircle2}
            label="Monitor de Categorias"
            active={activeTab === 'monitored_categories'}
            onClick={() => navigateTab('monitored_categories')}
          />
          <SidebarItem
            icon={Search}
            label="Comparativa"
            active={activeTab === 'search'}
            onClick={() => navigateTab('search')}
          />
          <SidebarItem
            icon={Radar}
            label="SKU"
            active={activeTab === 'cross'}
            onClick={() => navigateTab('cross')}
          />
          <SidebarItem
            icon={Layers}
            label="Categorias"
            active={activeTab === 'category'}
            onClick={() => navigateTab('category')}
          />
          <SidebarItem
            icon={Images}
            label="Banners"
            active={activeTab === 'banners'}
            onClick={() => navigateTab('banners')}
          />
          <div className="sidebar-spacer" />
          <SidebarItem
            icon={Package}
            label="Marcas"
            active={activeTab === 'settings'}
            onClick={() => navigateTab('settings')}
          />
        </nav>
      </aside>

      <main className="main-content">
        <header className="content-header">
          <div style={{ display: 'flex', alignItems: 'center' }}>
            <button className="mobile-header-toggle" onClick={() => setIsMobileSidebarOpen(true)}>
              <Menu size={24} />
            </button>
            <h1>{
              activeTab === 'monitor' ? 'Painel de Monitoramento' :
                activeTab === 'search' ? 'Busca Comparativa' :
                  activeTab === 'cross' ? 'Busca por SKU' :
                    activeTab === 'monitored_categories' ? 'Monitor de Categorias' :
                      activeTab === 'category' ? 'Varredura por Categoria' :
                        activeTab === 'banners' ? 'Banners' :
                        'Gerenciar Marcas'
            }
            </h1>
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

