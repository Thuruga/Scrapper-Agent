import { ApiClient, type ReviewComment, type ReviewCommentsResult, type StockDepthResult, type StockRuptureSummary } from './client';

export const phase44ClientTypecheck = {
  summary: null as StockRuptureSummary | null,
  depth: null as StockDepthResult | null,
  comment: null as ReviewComment | null,
  reviews: null as ReviewCommentsResult | null,
  getSummary: () => ApiClient.getMonitoredCategoryStockSummary('monitor-1'),
  requestDepth: () => ApiClient.requestMonitoredProductStockDepth('monitor-1', 'product-1'),
  requestReviews: () => ApiClient.requestMonitoredProductReviews('monitor-1', 'product-1', 1),
};
