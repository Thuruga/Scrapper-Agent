/* eslint-disable @typescript-eslint/no-explicit-any */
const API_BASE_URL = import.meta.env.VITE_API_URL || '';
export const API_KEY = import.meta.env.VITE_API_KEY || 'dev-key-123';

export class ApiClient {
  public static async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const headers = {
      'Content-Type': 'application/json',
      'X-API-Key': API_KEY,
      ...options.headers,
    };

    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      ...options,
      headers,
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

  // Brands
  static getBrands() {
    return this.request<any[]>('/brands/');
  }

  static saveBrand(data: any) {
    return this.request('/brands/', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  // Search
  static search(payload: { query: string; brands?: string[]; max_per_brand?: number; sort?: string; only_in_stock?: boolean }) {
    return this.request<any>('/search', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  static async exportSearch(payload: { query: string; brands?: string[]; max_per_brand?: number; sort?: string; only_in_stock?: boolean }) {
    const response = await fetch(`${API_BASE_URL}/search/export`, {
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
      } catch (e) {}
      throw new Error(errorMsg);
    }

    let filename = 'busca_comparativa.xlsx';
    const disposition = response.headers.get('content-disposition');
    if (disposition && disposition.includes('filename=')) {
      const matches = disposition.match(/filename="([^"]+)"/);
      if (matches && matches[1]) {
        filename = matches[1];
      }
    }

    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
  }

  // Monitors
  static getMonitors() {
    return this.request<any[]>('/monitors');
  }

  static startMonitor(data: any) {
    return this.request('/monitor/start', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  static deleteMonitor(jobId: string) {
    return this.request(`/monitor/${jobId}`, {
      method: 'DELETE',
    });
  }

  // Scrape
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

  static discoverCategories(brand: string) {
    return this.request<any>(`/brands/${brand}/auto-discovery`);
  }

  static deleteBrand(brand: string) {
    return this.request(`/brands/${brand}`, {
      method: 'DELETE',
    });
  }
}



