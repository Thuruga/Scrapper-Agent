const API_BASE_URL = import.meta.env.VITE_API_URL || '';
export const API_KEY = import.meta.env.VITE_API_KEY || 'dev-key-123';

export class ApiClient {
  private static async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const headers = {
      'Content-Type': 'application/json',
      'X-API-Key': API_KEY,
      ...options.headers,
    };

    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      ...options,
      headers,
    });

    let data: any = null;
    try {
      data = await response.json();
    } catch (err) {
      data = null;
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

  static discoverCategories(brand: str) {
    return this.request<any>(`/brands/${brand}/auto-discovery`);
  }
}

