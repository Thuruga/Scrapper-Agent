/* eslint-disable @typescript-eslint/no-explicit-any */
const API_BASE_URL = import.meta.env.VITE_API_URL || '';
const API_KEY = import.meta.env.VITE_API_KEY || 'dev-api-key';
// Janela para o browser iniciar o download antes de liberar o blob URL (IN-03).
const BLOB_REVOKE_DELAY_MS = 100;

export class ApiClient {

  // ------------------------------------------------------------------
  // Core request
  // ------------------------------------------------------------------
  public static async request<T>(endpoint: string, options: RequestInit = {}, signal?: AbortSignal): Promise<T> {
    const headers: any = {
      'Content-Type': 'application/json',
      'X-API-Key': API_KEY,
      ...options.headers,
    };

    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      ...options,
      headers,
      ...(signal ? { signal } : {}),
    });

    let data: any;
    try {
      data = await response.json();
    } catch {
      // Ignored
    }

    if (!response.ok) {
      throw new Error(data?.detail || `API Error: ${response.status}`);
    }

    return data as T;
  }

  // ------------------------------------------------------------------
  // Brands
  // ------------------------------------------------------------------
  static getBrands() {
    return this.request<any[]>('/brands/');
  }

  static saveBrand(data: any) {
    return this.request('/brands/', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  static deleteBrand(brand: string) {
    return this.request(`/brands/${encodeURIComponent(brand)}`, {
      method: 'DELETE',
    });
  }

  static setBrandActive(brandKey: string, isActive: boolean) {
    return this.request(`/brands/${encodeURIComponent(brandKey)}/active`, {
      method: 'PATCH',
      body: JSON.stringify({ is_active: isActive }),
    });
  }

  // ------------------------------------------------------------------
  // Search
  // ------------------------------------------------------------------
  static crossMarketplaceSearch(payload: { target_sku: string; search_query?: string; broad_query?: string; min_score?: number; zipcode?: string }, signal?: AbortSignal) {
    return this.request<any>('/search/cross-marketplace', {
      method: 'POST',
      body: JSON.stringify(payload),
    }, signal);
  }

  static calculateSingleShipping(payload: { marketplace: string; url: string; zipcode: string }) {
    return this.request<any>('/search/calculate-shipping', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  static search(payload: { query: string; brands?: string[]; max_per_brand?: number; sort?: string; only_in_stock?: boolean; zipcode?: string; include_shipping?: boolean }, signal?: AbortSignal) {
    return this.request<any>('/search', {
      method: 'POST',
      body: JSON.stringify(payload),
    }, signal);
  }

  static getHistoryList() {
    return this.request<any[]>('/history');
  }

  static getHistoryDetail(jobId: string) {
    return this.request<any>(`/history/${jobId}`);
  }

  static deleteHistory(jobId: string) {
    return this.request(`/history/${jobId}`, {
      method: 'DELETE',
    });
  }

  // ------------------------------------------------------------------
  // Desktop banners (Phase 34)
  // ------------------------------------------------------------------
  static startBannerJob(brands: string[]) {
    return this.request<any>('/banners/jobs', {
      method: 'POST',
      body: JSON.stringify({ brands }),
    });
  }

  static getBannerJob(jobId: string) {
    return this.request<any>(`/banners/jobs/${encodeURIComponent(jobId)}`);
  }

  static stopBannerJob(jobId: string) {
    return this.request(`/banners/jobs/${encodeURIComponent(jobId)}/stop`, { method: 'POST' });
  }

  static approveBannerJob(jobId: string, bannerIds: string[]) {
    return this.request<any>(`/banners/jobs/${encodeURIComponent(jobId)}/approve`, {
      method: 'POST',
      body: JSON.stringify({ banner_ids: bannerIds }),
    });
  }

  static getBannerHistory() {
    return this.request<any[]>('/banners/history');
  }

  static getBannerHistoryDetail(jobId: string) {
    return this.request<any>(`/banners/history/${encodeURIComponent(jobId)}`);
  }

  static deleteBannerHistory(jobId: string) {
    return this.request(`/banners/history/${encodeURIComponent(jobId)}`, { method: 'DELETE' });
  }

  private static async protectedBlob(endpoint: string): Promise<Blob> {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      headers: { 'X-API-Key': API_KEY },
    });
    if (!response.ok) {
      let detail = `API Error: ${response.status}`;
      try { detail = (await response.json())?.detail || detail; } catch { /* non-JSON body */ }
      throw new Error(detail);
    }
    return response.blob();
  }

  static getBannerAssetBlob(jobId: string, bannerId: string) {
    return this.protectedBlob(`/banners/assets/${encodeURIComponent(jobId)}/${encodeURIComponent(bannerId)}`);
  }

  static getBannerScreenshotBlob(jobId: string, brandKey: string) {
    return this.protectedBlob(`/banners/screenshots/${encodeURIComponent(jobId)}/${encodeURIComponent(brandKey)}`);
  }

  static getBannerReportBlob(jobId: string, format: 'json' | 'csv' | 'html') {
    return this.protectedBlob(`/banners/runs/${encodeURIComponent(jobId)}/reports/${format}`);
  }

  static async openProtectedBlob(blobPromise: Promise<Blob>) {
    const target = window.open('about:blank', '_blank');
    if (target) target.opener = null;
    try {
      const blob = await blobPromise;
      const url = window.URL.createObjectURL(blob);
      if (target) target.location.href = url;
      else window.location.href = url;
      setTimeout(() => window.URL.revokeObjectURL(url), 60_000);
    } catch (error) {
      target?.close();
      throw error;
    }
  }

  // Helper compartilhado de export → download de blob (IN-02): POST autenticado,
  // tratamento de erro, extração de filename do content-disposition e download via <a>.
  private static async downloadExport(
    endpoint: string,
    payload: any,
    defaultFilename: string,
    context: string,
  ): Promise<void> {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': API_KEY,
      },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      let errorMsg = `Export failed: ${response.status}`;
      try {
        const data = await response.json();
        if (data.detail) errorMsg = data.detail;
      } catch (_parseErr) {
        // Non-JSON error body; fall through with the status-based message.
        console.warn(`${context}: could not parse error response body`, _parseErr);
      }
      throw new Error(errorMsg);
    }

    let filename = defaultFilename;
    const disposition = response.headers.get('content-disposition');
    if (disposition && disposition.includes('filename=')) {
      const matches = disposition.match(/filename="([^"]+)"/);
      if (matches && matches[1]) filename = matches[1];
    }

    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    // Allow the browser to initiate the download before releasing the blob URL.
    setTimeout(() => {
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    }, BLOB_REVOKE_DELAY_MS);
  }

  static exportSearch(payload: { query: string; brands?: string[]; max_per_brand?: number; sort?: string; only_in_stock?: boolean; zipcode?: string; include_shipping?: boolean }): Promise<void> {
    return this.downloadExport('/search/export', payload, 'busca_comparativa.xlsx', 'exportSearch');
  }

  static exportCrossMarketplace(payload: { items: any[]; search_query?: string; target_sku: string }): Promise<void> {
    return this.downloadExport('/search/cross-marketplace/export', payload, 'busca_sku.xlsx', 'exportCrossMarketplace');
  }

  // ------------------------------------------------------------------
  // Monitors
  // ------------------------------------------------------------------
  static getMonitors() {
    return this.request<any[]>('/monitors');
  }

  static startMonitor(data: any) {
    return this.request('/monitor/start', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  static stopMonitor(jobId: string) {
    return this.request(`/monitor/stop/${jobId}`, {
      method: 'POST',
    });
  }

  static resumeMonitor(jobId: string) {
    return this.request(`/monitor/resume/${jobId}`, {
      method: 'POST',
    });
  }

  static deleteMonitor(jobId: string) {
    return this.request(`/monitor/${jobId}`, {
      method: 'DELETE',
    });
  }

  // ------------------------------------------------------------------
  // Monitored Categories (Fase 17)
  // ------------------------------------------------------------------
  static getMonitoredCategories() {
    return this.request<any[]>('/monitor/categories');
  }

  static createMonitoredCategory(data: { url: string; brand: string }) {
    return this.request('/monitor/category', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  static deleteMonitoredCategory(monitorId: string) {
    return this.request(`/monitor/category/${monitorId}`, {
      method: 'DELETE',
    });
  }

  static getMonitoredCategoryProducts(monitorId: string) {
    return this.request<any[]>(`/monitor/category/${monitorId}/products`);
  }

  // ------------------------------------------------------------------
  // Scrape
  // ------------------------------------------------------------------
  static startScrape(payload: any, multi = false) {
    const endpoint = multi ? '/scrape-category-multi' : '/scrape-category';
    return this.request(endpoint, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  static async getCanonicalCategories() {
    const data: any = await this.request('/canonical-categories');
    return data?.categories || [];
  }
}
