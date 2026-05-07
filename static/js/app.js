/**
 * App Initialization
 */
document.addEventListener('DOMContentLoaded', () => {
    console.log('E-Scraper Frontend Initializing...');
    
    // Initialize UI
    UI.init();

    // Global helpers for inline onclicks (until refactored to addEventListener)
    window.switchTab = (id) => UI.switchTab(id);
    window.stopMonitoring = (id) => UI.stopMonitoring(id);
    window.deleteMonitor = (id) => UI.deleteMonitor(id);
    window.cancelJob = () => UI.cancelJob();
    window.downloadFile = () => {
        if (window.lastOutputFile) window.location.href = '/' + window.lastOutputFile;
        else alert('Nenhum arquivo gerado.');
    };
    window.exportComparison = () => UI.exportComparison();
});
