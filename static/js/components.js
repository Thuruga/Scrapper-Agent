/**
 * Components - UI templates for dynamic rendering.
 */
class Components {
    static monitorCard(jobId, config, brandMeta) {
        const isActive = config.active;
        const lastPrice = config.last_price ? `R$ ${config.last_price.toFixed(2)}` : '---';
        const productName = config.product_name || (config.url ? config.url.split('/').filter(p => p).pop().toUpperCase() : 'PRODUTO');
        
        return `
            <div class="monitor-card" id="card-${jobId}">
                <span class="status-tag ${isActive ? 'status-active' : 'status-stopped'}" id="status-${jobId}">
                    ${isActive ? 'Ativo' : 'Parado'}
                </span>
                <div class="badge ${config.brand}">${brandMeta.name}</div>
                <div style="display: flex; gap: 1.2rem; align-items: center; margin-top: 0.2rem;">
                    <img src="${config.image_url || ''}" class="product-thumb" style="width: 60px; height: 60px; border-radius: 12px; background: rgba(255,255,255,0.05); object-fit: contain; display: ${config.image_url ? 'block' : 'none'}; border: 1px solid rgba(255,255,255,0.1);">
                    <div style="flex: 1; min-width: 0;">
                        <div style="font-weight: 600; font-size: 0.95rem; line-height: 1.3; margin-bottom: 0.3rem; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;" title="${productName}">
                            ${productName}
                        </div>
                        <div style="font-size: 0.75rem; color: var(--text-muted); text-overflow: ellipsis; white-space: nowrap; overflow: hidden; opacity: 0.7;">
                            ${config.url || ''}
                        </div>
                    </div>
                </div>

                <div style="display: flex; align-items: baseline; gap: 0.5rem;">
                    <div class="price" id="price-${jobId}">${lastPrice}</div>
                    <div style="font-size: 0.75rem; color: var(--text-muted);">
                        / ${config.interval_minutes}m
                    </div>
                </div>
                
                <div class="history-mini" id="history-${jobId}">
                    ${this.historyEntries(config.history)}
                </div>

                <div style="display: flex; gap: 0.75rem; margin-top: 0.5rem;">
                    <button class="tab-btn" style="padding: 0.6rem; flex: 1; font-size: 0.85rem; background: rgba(239, 68, 68, 0.15); color: #fca5a5; border: 1px solid rgba(239, 68, 68, 0.1);" onclick="UI.stopMonitoring('${jobId}')" id="stop-btn-${jobId}" ${!isActive ? 'disabled' : ''}>
                        Parar
                    </button>
                    <button class="tab-btn" style="padding: 0.6rem; font-size: 0.85rem; background: rgba(255, 255, 255, 0.08); color: var(--text-muted); border: 1px solid rgba(255,255,255,0.05);" onclick="UI.deleteMonitor('${jobId}')">
                        🗑️
                    </button>
                </div>
            </div>
        `;
    }

    static historyEntries(history) {
        if (!history || history.length === 0) {
            return '<div style="text-align: center; opacity: 0.5; padding: 0.5rem;">Aguardando check...</div>';
        }
        return history.slice().reverse().map(e => `
            <div class="history-entry">
                <span style="color: #6ee7b7; font-weight: 600;">R$ ${e.price.toFixed(2)}</span>
                <span style="opacity: 0.5;">${new Date(e.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
            </div>`).join('');
    }

    static brandChip(brand, color, isChecked = false) {
        return `
            <label class="brand-checkbox ${brand.brand_key}-check">
                <input type="checkbox" name="orchBrand" value="${brand.brand_key}" ${isChecked ? 'checked' : ''}>
                <span class="brand-chip">
                    <span class="chip-dot" style="background:${color};"></span>
                    ${brand.brand_name}
                </span>
            </label>
        `;
    }

    static searchBrandOption(brand, isChecked = true) {
        return `
            <label><input type="checkbox" value="${brand.brand_key}" ${isChecked ? 'checked' : ''}> ${brand.brand_name}</label>
        `;
    }

    static brandItem(brand) {
        const mappings = brand.mappings.map(m => `<span class="mapping-badge">${m.canonical_slug}</span>`).join('');
        return `
            <div class="brand-item">
                <div class="brand-item-info">
                    <span class="brand-item-name">${brand.brand_name}</span>
                    <span class="brand-item-domain">${brand.domain}</span>
                </div>
                <div style="display:flex; gap:0.5rem; flex-wrap:wrap;">
                    ${mappings}
                </div>
            </div>
        `;
    }

    static brandStatusBadge(brandKey, brandName, color) {
        return `
            <div class="brand-status-badge running" id="badge-${brandKey}">
                <span class="badge-dot" style="background:${color};"></span>
                <span>${brandName}</span>
                <span class="badge-stats" id="badge-stats-${brandKey}">Varrendo...</span>
            </div>
        `;
    }

    static deparaRow(brandName, color, url) {
        return `
            <div class="depara-row">
                <span class="depara-brand"><span class="chip-dot" style="background:${color};opacity:1;"></span>${brandName}</span>
                <span class="depara-arrow">→</span>
                <span class="depara-url">${url}</span>
            </div>
        `;
    }

    static productCard(product, isCheapest) {
        const hasDiscount = product.price_discount != null && product.price_full != null && product.price_discount < product.price_full;
        const effectivePrice = hasDiscount ? product.price_discount : product.price_full;
        
        const priceStr = effectivePrice != null
            ? `R$ ${effectivePrice.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}`
            : '<span style="color:var(--text-muted);font-size:0.85rem;">Preço não disponível</span>';

        const originalStr = hasDiscount
            ? `<span class="price-discount">R$ ${product.price_full.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}</span>`
            : '';

        const discountPct = hasDiscount ? Math.round((1 - product.price_discount / product.price_full) * 100) : 0;
        const discountBadge = discountPct > 0
            ? `<span style="background:rgba(239,68,68,0.2);color:#fca5a5;border:1px solid rgba(239,68,68,0.35);border-radius:4px;font-size:0.7rem;font-weight:700;padding:0.1rem 0.4rem;">-${discountPct}%</span>`
            : '';

        const avDot = product.available != null
            ? `<span class="availability-dot ${product.available ? 'av-true' : 'av-false'}" title="${product.available ? 'Disponível' : 'Indisponível'}"></span>`
            : '';

        const thumb = product.image_url
            ? `<img class="product-thumb" src="${product.image_url}" alt="" loading="lazy" onerror="this.style.display='none'">`
            : `<div class="product-thumb-placeholder">👕</div>`;

        const ratingHtml = (product.rating != null)
            ? `<div class="rating-row">
                <div class="rating-stars">${this.stars(product.rating)}</div>
                <span style="font-weight:600;">${product.rating.toFixed(1)}</span>
                <span class="rating-count">(${product.review_count || 0})</span>
               </div>`
            : '';

        return `
            <a class="product-card ${isCheapest ? 'cheapest' : ''}" href="${product.url}" target="_blank" rel="noopener">
                ${thumb}
                <div class="product-info">
                    <div class="product-title">${product.product_name}</div>
                    ${product.category ? `<div class="product-category">${product.category}</div>` : ''}
                    ${ratingHtml}
                    <div class="product-price-row">
                        <span class="price-full">${priceStr}</span>
                        ${originalStr}
                        ${discountBadge}
                        ${avDot}
                    </div>
                </div>
            </a>`;
    }

    static stars(rating) {
        let stars = '';
        const rounded = Math.round(rating);
        for (let i = 1; i <= 5; i++) {
            stars += i <= rounded ? '★' : '☆';
        }
        return stars;
    }
}

window.Components = Components;
