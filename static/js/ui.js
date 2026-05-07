/**
 * UI - Handles state management, event listeners, and DOM updates.
 */
class UI {
    static state = {
        brands: [],
        brandColors: {},
        brandMeta: {},
        monitorWebSockets: {},
        orchestrator: {
            ws: null,
            currentJobId: null,
            totalLinks: 0,
            processedLinks: 0,
            successCount: 0,
            errorCount: 0,
            brandStatusMap: {}
        },
        lastComparisonData: null,
        lastSingleBrand: null
    };

    static init() {
        this.bindEvents();
        this.loadInitialData();
    }

    static bindEvents() {
        // Tab switching
        document.querySelectorAll('.tab-btn').forEach(btn => {
            const tabId = btn.getAttribute('onclick').match(/'([^']+)'/)[1];
            btn.onclick = () => this.switchTab(tabId);
        });

        // Monitor Form
        const monitorForm = document.getElementById('monitorForm');
        if (monitorForm) {
            monitorForm.onsubmit = (e) => this.handleMonitorSubmit(e);
        }

        // Orchestrator Form
        const orchestratorForm = document.getElementById('orchestratorForm');
        if (orchestratorForm) {
            orchestratorForm.onsubmit = (e) => this.handleOrchestratorSubmit(e);
        }

        // Compare Form
        const compareForm = document.getElementById('compareForm');
        if (compareForm) {
            compareForm.onsubmit = (e) => this.handleCompareSubmit(e);
        }

        // Brand Form
        const brandForm = document.getElementById('brandForm');
        if (brandForm) {
            brandForm.onsubmit = (e) => this.handleBrandSubmit(e);
        }

        // Canonical Category change
        const canonicalSelect = document.getElementById('orchCanonicalCategory');
        if (canonicalSelect) {
            canonicalSelect.onchange = () => this.updateDeparaPreview();
        }
    }

    static async loadInitialData() {
        await this.loadBrands();
        await this.loadExistingMonitors();
        await this.loadCanonicalCategories();
        this.switchCategoryMode();
    }

    // --- Tab Management ---
    static switchTab(tabId) {
        document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));

        const activeBtn = document.querySelector(`.tab-btn[onclick*="'${tabId}'"]`);
        if (activeBtn) activeBtn.classList.add('active');
        
        const activeContent = document.getElementById(`tab-${tabId}`);
        if (activeContent) activeContent.classList.add('active');
    }

    // --- Brand Management ---
    static async loadBrands() {
        try {
            const brands = await ApiService.getBrands();
            this.state.brands = brands;

            const colors = ['#3b82f6', '#ef4444', '#10b981', '#f59e0b', '#c084fc', '#06b6d4'];
            brands.forEach((b, i) => {
                const color = colors[i % colors.length];
                this.state.brandColors[b.brand_key] = { color, name: b.brand_name };
                this.state.brandMeta[b.brand_key] = { name: b.brand_name, cls: b.brand_key, emoji: '📦' };
            });

            this.updateBrandUI(brands);
        } catch (e) {
            console.error('Error loading brands:', e);
        }
    }

    static updateBrandUI(brands) {
        // Monitor Select
        const monitorSelect = document.getElementById('brand');
        if (monitorSelect) {
            monitorSelect.innerHTML = brands.map(b => `<option value="${b.brand_key}">${b.brand_name}</option>`).join('');
        }

        // Multi-Brand Selector
        const multiSelector = document.getElementById('multiBrandSelector');
        if (multiSelector) {
            multiSelector.innerHTML = brands.map(b => Components.brandChip(b, this.state.brandColors[b.brand_key].color)).join('');
            // Add listeners to new chips
            multiSelector.querySelectorAll('input').forEach(input => {
                input.onchange = () => this.switchCategoryMode();
            });
        }

        // Search Checkboxes
        const searchOptions = document.getElementById('compareBrandOptions');
        if (searchOptions) {
            searchOptions.innerHTML = brands.map(b => Components.searchBrandOption(b)).join('') + `
                <div class="max-input">
                    <span style="font-size:0.85rem;color:var(--text-muted);">Resultados por marca:</span>
                    <input type="number" id="maxPerBrand" value="10" min="1" max="50">
                </div>
            `;
        }

        // Settings List
        const brandList = document.getElementById('brandList');
        if (brandList) {
            brandList.innerHTML = brands.map(b => Components.brandItem(b)).join('');
        }
    }

    static async handleBrandSubmit(e) {
        e.preventDefault();
        const btn = document.getElementById('saveBrandBtn');
        const btnText = btn.querySelector('.btn-text');
        
        const payload = {
            brand_key: document.getElementById('b_key').value,
            brand_name: document.getElementById('b_name').value,
            domain: document.getElementById('b_domain').value
        };

        btn.classList.add('button-loading');
        try {
            await ApiService.saveBrand(payload);
            alert('Marca salva com sucesso! O mapeamento ocorrerá em segundo plano.');
            e.target.reset();
            setTimeout(() => this.loadBrands(), 2000);
        } catch (err) {
            alert('Erro: ' + err.message);
        } finally {
            btn.classList.remove('button-loading');
        }
    }

    // --- Monitor Management ---
    static async loadExistingMonitors() {
        try {
            const monitors = await ApiService.getMonitors();
            Object.keys(monitors).forEach(jobId => {
                if (monitors[jobId]) {
                    this.addMonitorCard(jobId, monitors[jobId]);
                }
            });
        } catch (e) {
            console.error('Error loading monitors:', e);
        }
    }

    static addMonitorCard(jobId, config) {
        const grid = document.getElementById('monitorGrid');
        const emptyState = document.getElementById('monitorEmptyState');
        if (emptyState) emptyState.style.display = 'none';

        const existing = document.getElementById(`card-${jobId}`);
        if (existing) existing.remove();

        const brandMeta = this.state.brandColors[config.brand] || { color: '#94a3b8', name: config.brand };
        const cardHtml = Components.monitorCard(jobId, config, brandMeta);
        
        if (grid) grid.insertAdjacentHTML('afterbegin', cardHtml);

        if (config.active) {
            this.connectMonitorWs(jobId);
        }
    }

    static connectMonitorWs(jobId) {
        if (this.state.monitorWebSockets[jobId]) return;

        const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
        const ws = new WebSocket(`${protocol}//${location.host}/ws/${jobId}`);
        this.state.monitorWebSockets[jobId] = ws;

        ws.onmessage = (event) => {
            const msg = JSON.parse(event.data);
            if (msg.type === 'price_update') {
                const priceEl = document.getElementById(`price-${jobId}`);
                if (priceEl) priceEl.textContent = `R$ ${msg.price.toFixed(2)}`;
                
                const historyEl = document.getElementById(`history-${jobId}`);
                if (historyEl) historyEl.innerHTML = Components.historyEntries(msg.history);
            } else if (msg.type === 'done') {
                const tag = document.getElementById(`status-${jobId}`);
                if (tag) {
                    tag.className = 'status-tag status-stopped';
                    tag.textContent = 'Concluído';
                }
                const btn = document.getElementById(`stop-btn-${jobId}`);
                if (btn) btn.disabled = true;
                ws.close();
            }
        };

        ws.onclose = () => delete this.state.monitorWebSockets[jobId];
    }

    static async handleMonitorSubmit(e) {
        e.preventDefault();
        const btn = document.getElementById('monitorSubmitBtn');
        const payload = {
            url: document.getElementById('url').value,
            brand: document.getElementById('brand').value,
            interval: parseInt(document.getElementById('interval').value),
            duration: parseInt(document.getElementById('duration').value)
        };

        btn.classList.add('button-loading');
        btn.disabled = true;

        try {
            const data = await ApiService.startMonitor(payload);
            this.addMonitorCard(data.job_id, data.config);
            alert("Monitor iniciado com sucesso!");
            e.target.reset();
        } catch (err) {
            alert("Erro: " + err.message);
        } finally {
            btn.classList.remove('button-loading');
            btn.disabled = false;
        }
    }

    static async stopMonitoring(jobId) {
        try {
            await ApiService.stopMonitor(jobId);
            const tag = document.getElementById(`status-${jobId}`);
            if (tag) {
                tag.className = 'status-tag status-stopped';
                tag.textContent = 'Parado';
            }
            const btn = document.getElementById(`stop-btn-${jobId}`);
            if (btn) btn.disabled = true;
            if (this.state.monitorWebSockets[jobId]) this.state.monitorWebSockets[jobId].close();
        } catch (e) {
            console.error('Error stopping monitor:', e);
        }
    }

    static async deleteMonitor(jobId) {
        if (!confirm('Tem certeza que deseja remover este produto do monitoramento?')) return;

        try {
            await ApiService.deleteMonitor(jobId);
            const card = document.getElementById(`card-${jobId}`);
            if (card) card.remove();
            if (this.state.monitorWebSockets[jobId]) this.state.monitorWebSockets[jobId].close();

            const grid = document.getElementById('monitorGrid');
            if (grid && grid.children.length === 0) {
                const emptyState = document.getElementById('monitorEmptyState');
                if (emptyState) emptyState.style.display = 'block';
            }
        } catch (e) {
            console.error('Error deleting monitor:', e);
        }
    }

    // --- Category Scraping ---
    static async loadCanonicalCategories() {
        const skeleton = document.getElementById('canonicalCategorySkeleton');
        const sel = document.getElementById('orchCanonicalCategory');
        if (skeleton) skeleton.style.display = 'block';
        if (sel) sel.style.display = 'none';

        try {
            const data = await ApiService.getCanonicalCategories();
            if (sel) {
                sel.innerHTML = '<option value="">Selecione uma categoria...</option>';
                data.categories.forEach(group => {
                    const og = document.createElement('optgroup');
                    og.label = group.group;
                    group.categories.forEach(cat => {
                        const opt = document.createElement('option');
                        opt.value = cat.slug;
                        opt.textContent = cat.label;
                        og.appendChild(opt);
                    });
                    sel.appendChild(og);
                });
            }
        } catch (e) {
            if (sel) sel.innerHTML = '<option value="">Erro ao carregar categorias</option>';
        } finally {
            if (skeleton) skeleton.style.display = 'none';
            if (sel) sel.style.display = 'block';
        }
    }

    static async loadSingleBrandCategories(brandKey) {
        const skeleton = document.getElementById('singleCategorySkeleton');
        const sel = document.getElementById('orchSingleCategory');
        if (skeleton) skeleton.style.display = 'block';
        if (sel) {
            sel.style.display = 'none';
            sel.innerHTML = '';
        }

        try {
            const data = await ApiService.getBrandCategories(brandKey);
            if (sel) {
                data.categories.forEach(group => {
                    const og = document.createElement('optgroup');
                    og.label = group.group;
                    group.items.forEach(item => {
                        const opt = document.createElement('option');
                        opt.value = item.path;
                        opt.textContent = item.label;
                        og.appendChild(opt);
                    });
                    sel.appendChild(og);
                });
            }
        } catch (e) {
            if (sel) sel.innerHTML = '<option value="">Erro ao carregar categorias</option>';
        } finally {
            if (skeleton) skeleton.style.display = 'none';
            if (sel) sel.style.display = 'block';
        }
    }

    static getSelectedBrands() {
        const brands = [];
        document.querySelectorAll('input[name="orchBrand"]:checked').forEach(el => brands.push(el.value));
        return brands;
    }

    static switchCategoryMode() {
        const brands = this.getSelectedBrands();
        const multi = brands.length > 1;

        const canonicalGroup = document.getElementById('canonicalCategoryGroup');
        const singleGroup = document.getElementById('singleBrandCategoryGroup');
        const deparaPreview = document.getElementById('deparaPreview');
        const orchBtnText = document.getElementById('orchBtnText');

        if (canonicalGroup) canonicalGroup.style.display = multi ? 'block' : 'none';
        if (singleGroup) singleGroup.style.display = multi ? 'none' : 'block';
        if (deparaPreview && !multi) deparaPreview.style.display = 'none';

        if (orchBtnText) {
            orchBtnText.textContent = multi ? '🚀 Iniciar Varredura Multi-Marca' : '🚀 Iniciar Varredura em Lote';
        }

        if (!multi && brands.length === 1 && brands[0] !== this.state.lastSingleBrand) {
            this.state.lastSingleBrand = brands[0];
            this.loadSingleBrandCategories(brands[0]);
        }
        
        if (multi) this.updateDeparaPreview();
    }

    static async updateDeparaPreview() {
        const slug = document.getElementById('orchCanonicalCategory').value;
        const brands = this.getSelectedBrands();
        const panel = document.getElementById('deparaPreview');
        const container = document.getElementById('deparaMappings');

        if (!slug || brands.length < 2) {
            if (panel) panel.style.display = 'none';
            return;
        }

        try {
            const data = await ApiService.getCategoryPreview({ category_slug: slug, brands });
            if (container) {
                container.innerHTML = data.mappings.map(m => {
                    const bc = this.state.brandColors[m.brand] || { color: '#94a3b8', name: m.brand };
                    return Components.deparaRow(bc.name, bc.color, m.url);
                }).join('');
            }
            if (panel) panel.style.display = 'block';
        } catch (e) {
            if (panel) panel.style.display = 'none';
        }
    }

    static async handleOrchestratorSubmit(e) {
        e.preventDefault();
        const brands = this.getSelectedBrands();
        if (brands.length === 0) { alert('Selecione ao menos uma marca.'); return; }

        const multi = brands.length > 1;
        let payload;

        if (multi) {
            const slug = document.getElementById('orchCanonicalCategory').value;
            if (!slug) { alert('Selecione uma categoria.'); return; }
            payload = { brands, category_slug: slug };
        } else {
            const path = document.getElementById('orchSingleCategory').value;
            if (!path) { alert('Selecione uma categoria.'); return; }
            payload = { brand: brands[0], category_path: path };
        }

        this.resetOrchestratorUI(brands);
        this.setJobRunning(true);

        try {
            const data = await ApiService.startCategoryScrape(payload, multi);
            this.state.orchestrator.currentJobId = data.job_id;
            this.logToConsole(`Job ${this.state.orchestrator.currentJobId} iniciado.`, 'info');

            const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
            const ws = new WebSocket(`${protocol}//${location.host}/ws/${this.state.orchestrator.currentJobId}`);
            this.state.orchestrator.ws = ws;
            ws.onmessage = (event) => this.handleWsMessage(JSON.parse(event.data));
            ws.onerror = () => {
                this.logToConsole('Erro WebSocket.', 'error');
                this.setJobRunning(false);
            };
        } catch (err) {
            this.logToConsole(`Erro: ${err.message}`, 'error');
            this.setJobRunning(false);
        }
    }

    static resetOrchestratorUI(brands) {
        const downloadArea = document.getElementById('downloadArea');
        const consoleFeed = document.getElementById('consoleFeed');
        const progressContainer = document.getElementById('progressContainer');

        if (downloadArea) downloadArea.style.display = 'none';
        if (consoleFeed) consoleFeed.innerHTML = '';
        
        this.state.orchestrator.totalLinks = 0;
        this.state.orchestrator.processedLinks = 0;
        this.state.orchestrator.successCount = 0;
        this.state.orchestrator.errorCount = 0;

        if (progressContainer) progressContainer.style.display = 'block';
        this.updateProgress();
        this.initBrandStatusBadges(brands);
        this.logToConsole(`Iniciando varredura: [${brands.join(', ')}]`, 'info');
    }

    static logToConsole(message, type = 'info', brand = null) {
        const feed = document.getElementById('consoleFeed');
        if (!feed) return;
        const line = document.createElement('div');
        let cls = `console-line ${type}`;
        if (brand) cls += ` brand-${brand}`;
        line.className = cls;
        line.textContent = `[${new Date().toLocaleTimeString()}] ${message}`;
        feed.appendChild(line);
        feed.scrollTop = feed.scrollHeight;
    }

    static updateProgress() {
        const { totalLinks, processedLinks, successCount, errorCount } = this.state.orchestrator;
        if (totalLinks === 0) return;
        
        const pct = (processedLinks / totalLinks) * 100;
        const fill = document.getElementById('progressFill');
        const text = document.getElementById('progressText');
        const statSuccess = document.getElementById('statSuccess');
        const statError = document.getElementById('statError');

        if (fill) fill.style.width = `${pct}%`;
        if (text) text.textContent = `${processedLinks} / ${totalLinks}`;
        if (statSuccess) statSuccess.textContent = `Sucessos: ${successCount}`;
        if (statError) statError.textContent = `Falhas: ${errorCount}`;
    }

    static initBrandStatusBadges(brands) {
        const container = document.getElementById('multiBrandStatus');
        if (!container) return;
        container.style.display = brands.length > 1 ? 'flex' : 'none';
        container.innerHTML = '';
        
        this.state.orchestrator.brandStatusMap = {};
        brands.forEach(bk => {
            const bc = this.state.brandColors[bk] || { color: '#94a3b8', name: bk };
            this.state.orchestrator.brandStatusMap[bk] = { success: 0, error: 0, total: 0 };
            container.insertAdjacentHTML('beforeend', Components.brandStatusBadge(bk, bc.name, bc.color));
        });
    }

    static updateBrandBadge(bk, status, text) {
        const badge = document.getElementById(`badge-${bk}`);
        const stats = document.getElementById(`badge-stats-${bk}`);
        if (badge) badge.className = `brand-status-badge ${status}`;
        if (stats && text) stats.textContent = text;
    }

    static setJobRunning(running) {
        const orchBtn = document.getElementById('orchBtn');
        const cancelBtn = document.getElementById('cancelBtn');
        if (orchBtn) {
            orchBtn.classList.toggle('button-loading', running);
            orchBtn.disabled = running;
        }
        if (cancelBtn) cancelBtn.classList.toggle('visible', running);
    }

    static async cancelJob() {
        const { currentJobId } = this.state.orchestrator;
        if (!currentJobId) return;
        
        const btn = document.getElementById('cancelBtn');
        btn.classList.add('button-loading');
        btn.disabled = true;

        try {
            await ApiService.cancelJob(currentJobId);
            this.logToConsole('⏹ Sinal de cancelamento enviado...', 'cancelled');
        } catch (e) {
            this.logToConsole('Erro ao cancelar: ' + e.message, 'error');
            btn.classList.remove('button-loading');
            btn.disabled = false;
            if (e.message.includes('404')) {
                this.setJobRunning(false);
                this.state.orchestrator.currentJobId = null;
            }
        }
    }

    static handleWsMessage(msg) {
        const brand = msg.brand || null;
        const orch = this.state.orchestrator;

        if (msg.type === 'brand_stats' && brand && orch.brandStatusMap[brand]) {
            orch.brandStatusMap[brand].total = msg.total_links;
            orch.totalLinks += msg.total_links;
            this.updateProgress();
            this.updateBrandBadge(brand, 'running', `0/${msg.total_links}`);
        }
        if (msg.type === 'stats' && msg.total_links) { orch.totalLinks = msg.total_links; this.updateProgress(); }

        if (msg.type === 'brand_success' && brand) {
            orch.processedLinks++; orch.successCount++;
            if (orch.brandStatusMap[brand]) {
                orch.brandStatusMap[brand].success++;
                const bs = orch.brandStatusMap[brand];
                this.updateBrandBadge(brand, 'running', `${bs.success + bs.error}/${bs.total}`);
            }
            this.updateProgress();
        }
        if (msg.type === 'success') { orch.processedLinks++; orch.successCount++; this.updateProgress(); }

        if (msg.type === 'brand_error' && brand) {
            orch.processedLinks++; orch.errorCount++;
            if (orch.brandStatusMap[brand]) {
                orch.brandStatusMap[brand].error++;
                const bs = orch.brandStatusMap[brand];
                this.updateBrandBadge(brand, 'running', `${bs.success + bs.error}/${bs.total}`);
            }
            this.updateProgress();
        }
        if (msg.type === 'error' && msg.message && msg.message.includes('Extração')) {
            orch.processedLinks++; orch.errorCount++; this.updateProgress();
        }

        if (msg.type === 'brand_done' && brand && orch.brandStatusMap[brand]) {
            this.updateBrandBadge(brand, 'completed', `✓ ${msg.success_count} produtos`);
        }

        if (msg.type === 'done' || msg.type === 'cancelled_done') {
            const cancelled = msg.type === 'cancelled_done';
            this.logToConsole(msg.message, cancelled ? 'cancelled' : 'stats');
            
            const msgEl = document.getElementById('downloadMsg');
            const area = document.getElementById('downloadArea');
            if (msgEl) {
                msgEl.innerHTML = cancelled ? '⚠️ Operação cancelada — dados parciais disponíveis.' : `✅ Extração concluída! ${msg.valid_products || ''} produtos.`;
                msgEl.style.color = cancelled ? 'var(--warning)' : 'var(--success)';
            }
            if (area) area.style.display = 'block';
            
            window.lastOutputFile = msg.output_file;
            this.setJobRunning(false);
            const cancelBtn = document.getElementById('cancelBtn');
            if (cancelBtn) {
                cancelBtn.classList.remove('button-loading');
                cancelBtn.disabled = false;
            }
            orch.currentJobId = null;
            if (orch.ws) orch.ws.close();
            return;
        }

        if (msg.type === 'cancelled' || msg.type === 'error_done') {
            this.logToConsole(msg.message, msg.type === 'error_done' ? 'error' : 'cancelled');
            this.setJobRunning(false);
            const cancelBtn = document.getElementById('cancelBtn');
            if (cancelBtn) {
                cancelBtn.classList.remove('button-loading');
                cancelBtn.disabled = false;
            }
            orch.currentJobId = null;
            if (orch.ws) orch.ws.close();
            return;
        }

        this.logToConsole(msg.message || JSON.stringify(msg), msg.type || 'info', brand);
    }

    // --- Search Management ---
    static async handleCompareSubmit(e) {
        e.preventDefault();
        const query = document.getElementById('searchQuery').value.trim();
        if (!query) return;

        const brands = Array.from(document.querySelectorAll('#compareBrandOptions input[type="checkbox"]:checked')).map(el => el.value);
        if (brands.length === 0) { alert('Selecione ao menos uma marca para buscar.'); return; }

        const maxPerBrand = parseInt(document.getElementById('maxPerBrand').value) || 10;
        const btn = document.getElementById('searchBtn');
        const exportBar = document.getElementById('exportBar');
        const idle = document.getElementById('searchIdle');
        const grid = document.getElementById('comparisonGrid');

        btn.classList.add('button-loading');
        btn.disabled = true;
        if (exportBar) exportBar.classList.remove('visible');
        if (idle) idle.style.display = 'none';
        if (grid) {
            grid.style.display = 'grid';
            this.renderSkeletonColumns(brands);
        }

        try {
            const data = await ApiService.search({ query, brands, max_per_brand: maxPerBrand });
            this.renderComparison(data);
        } catch (err) {
            if (grid) {
                grid.innerHTML = `<div style="grid-column:1/-1;text-align:center;color:var(--error);padding:3rem;">⚠️ Erro na busca: ${err.message}</div>`;
            }
        } finally {
            btn.classList.remove('button-loading');
            btn.disabled = false;
        }
    }

    static renderSkeletonColumns(brands) {
        const grid = document.getElementById('comparisonGrid');
        grid.innerHTML = '';
        brands.forEach(brandKey => {
            const meta = this.state.brandMeta[brandKey] || { name: brandKey, cls: '', emoji: '⚪' };
            grid.insertAdjacentHTML('beforeend', `
                <div class="brand-column">
                    <div class="brand-header ${meta.cls}">
                        <div class="brand-header-info">
                            <span class="brand-dot"></span>
                            <span class="brand-name">${meta.name}</span>
                        </div>
                        <span class="brand-status loading">Buscando…</span>
                    </div>
                    <div class="brand-products">
                        ${[1, 2, 3].map(() => '<div class="skeleton-card"></div>').join('')}
                    </div>
                </div>
            `);
        });
    }

    static renderComparison(data) {
        this.state.lastComparisonData = data;
        const grid = document.getElementById('comparisonGrid');
        grid.innerHTML = '';

        let globalMin = Infinity;
        data.results.forEach(br => {
            br.products.forEach(p => {
                const hasDiscount = p.price_discount != null && p.price_full != null && p.price_discount < p.price_full;
                const effective = hasDiscount ? p.price_discount : p.price_full;
                if (effective != null && effective > 0 && effective < globalMin) globalMin = effective;
            });
        });

        let totalProducts = 0;
        data.results.forEach(brandResult => {
            const meta = this.state.brandMeta[brandResult.brand_key] || { name: brandResult.brand_key, cls: '', emoji: '⚪' };
            totalProducts += brandResult.total_found;

            let statusLabel, statusCls, bodyHtml;

            if (brandResult.error) {
                statusLabel = 'Erro';
                statusCls = 'error';
                bodyHtml = `<div class="brand-empty"><svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg><span>${brandResult.error}</span></div>`;
            } else if (brandResult.products.length === 0) {
                statusLabel = 'Sem resultados';
                statusCls = 'empty';
                bodyHtml = `<div class="brand-empty"><svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg><span>Nenhum produto encontrado para "${data.query}"</span></div>`;
            } else {
                statusLabel = `${brandResult.total_found} produto${brandResult.total_found !== 1 ? 's' : ''}`;
                statusCls = 'done';
                bodyHtml = brandResult.products.map(p => {
                    const hasDiscount = p.price_discount != null && p.price_full != null && p.price_discount < p.price_full;
                    const effective = hasDiscount ? p.price_discount : p.price_full;
                    const isCheapest = effective != null && effective > 0 && Math.abs(effective - globalMin) < 0.01;
                    return Components.productCard(p, isCheapest);
                }).join('');
            }

            grid.insertAdjacentHTML('beforeend', `
                <div class="brand-column">
                    <div class="brand-header ${meta.cls}">
                        <div class="brand-header-info">
                            <span class="brand-dot"></span>
                            <span class="brand-name">${meta.name}</span>
                        </div>
                        <span class="brand-status ${statusCls}">${statusLabel}</span>
                    </div>
                    <div class="brand-products">${bodyHtml}</div>
                </div>
            `);
        });

        const summary = document.getElementById('exportSummary');
        if (summary) summary.textContent = `${totalProducts} produtos encontrados em ${data.results.length} marcas.`;
        const bar = document.getElementById('exportBar');
        if (bar) bar.classList.add('visible');
    }

    static exportComparison() {
        const data = this.state.lastComparisonData;
        if (!data) return;
        const rows = [['Marca', 'Produto', 'Preço Cheio', 'Preço Desconto', 'Disponível', 'Categoria', 'URL']];
        data.results.forEach(br => {
            br.products.forEach(p => {
                rows.push([
                    br.brand_name,
                    `"${(p.product_name || '').replace(/"/g, '""')}"`,
                    p.price_full ?? '',
                    p.price_discount ?? '',
                    p.available != null ? (p.available ? 'Sim' : 'Não') : '',
                    p.category ?? '',
                    p.url ?? ''
                ]);
            });
        });
        const csv = rows.map(r => r.join(',')).join('\n');
        const blob = new Blob(['\uFEFF' + csv], { type: 'text/csv;charset=utf-8;' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `comparacao_${data.query.replace(/\s+/g, '_')}_${Date.now()}.csv`;
        a.click();
        URL.revokeObjectURL(url);
    }
}

window.UI = UI;
