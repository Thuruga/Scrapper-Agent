/**
 * ApiService - Centralizes all backend communication.
 * Robust, professional, and reusable.
 */
class ApiService {
    static async request(endpoint, options = {}) {
        const defaultOptions = {
            headers: { 'Content-Type': 'application/json' },
        };
        const finalOptions = { ...defaultOptions, ...options };
        
        try {
            const response = await fetch(endpoint, finalOptions);
            const data = await response.json().catch(() => ({}));
            
            if (!response.ok) {
                throw new Error(data.detail || `HTTP error! status: ${response.status}`);
            }
            return data;
        } catch (error) {
            console.error(`API Request Error [${endpoint}]:`, error);
            throw error;
        }
    }

    // Brands
    static async getBrands() {
        return this.request('/brands/');
    }

    static async saveBrand(brandData) {
        return this.request('/brands/', {
            method: 'POST',
            body: JSON.stringify(brandData)
        });
    }

    static async getBrandCategories(brandKey) {
        return this.request(`/brands/${brandKey}/categories`);
    }

    // Monitors
    static async getMonitors() {
        return this.request('/monitors');
    }

    static async startMonitor(monitorData) {
        return this.request('/monitor/start', {
            method: 'POST',
            body: JSON.stringify(monitorData)
        });
    }

    static async stopMonitor(jobId) {
        return this.request(`/monitor/stop/${jobId}`, { method: 'POST' });
    }

    static async deleteMonitor(jobId) {
        return this.request(`/monitor/${jobId}`, { method: 'DELETE' });
    }

    // Categories
    static async getCanonicalCategories() {
        return this.request('/canonical-categories');
    }

    static async getCategoryPreview(payload) {
        return this.request('/category-preview', {
            method: 'POST',
            body: JSON.stringify(payload)
        });
    }

    // Scraping / Jobs
    static async startCategoryScrape(payload, multi = false) {
        const endpoint = multi ? '/scrape-category-multi' : '/scrape-category';
        return this.request(endpoint, {
            method: 'POST',
            body: JSON.stringify(payload)
        });
    }

    static async cancelJob(jobId) {
        return this.request(`/jobs/${jobId}`, { method: 'DELETE' });
    }

    // Search
    static async search(payload) {
        return this.request('/search', {
            method: 'POST',
            body: JSON.stringify(payload)
        });
    }
}

window.ApiService = ApiService;
