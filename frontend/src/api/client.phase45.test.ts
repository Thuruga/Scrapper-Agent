import {
  ApiClient,
  type SortimentCategoryRow,
  type SortimentDashboardResponse,
  type SortimentManualRunResponse,
} from './client';

export async function assertPhase45ClientContracts() {
  const categories: SortimentCategoryRow[] = await ApiClient.getSortimentCategories();
  const synced: SortimentCategoryRow[] = await ApiClient.syncSortimentCategories();
  const updated: SortimentCategoryRow = await ApiClient.updateSortimentCategory(
    'sortiment-1',
    true,
  );
  const runResult: SortimentManualRunResponse = await ApiClient.runSortimentCategory(
    'sortiment-1',
  );
  const dashboard: SortimentDashboardResponse = await ApiClient.getSortimentDashboard(
    'sortiment-1',
  );

  void categories;
  void synced;
  void updated;
  void runResult;
  void dashboard;
}
