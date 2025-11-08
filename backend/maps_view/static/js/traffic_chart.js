/**
 * Traffic Chart Module - Professional Grafana Style (v3.2.2)
 * (c) DriveMaps / MapsProve Integration
 *
 * Highlights v3.2.2:
 *  - Lazy loading Chart.js on demand
 *  - Optional compact mode (dashboard-friendly)
 *  - Per-instance theming
 *  - Incremental auto-refresh (delta via latest timestamp)
 *  - Global callbacks onModalOpened / onModalClosed
 */

class TrafficChartManager {
    constructor() {
        this.instances = new Map();
    this.defaultPeriod = 1; // hours
    // Periods now strictly expressed in HOURS (keys = displayed string, value = hours)
    this.availablePeriods = [1, 24, 168, 720]; // 24h, 7d, 30d expressed in hours
        this.localStorageKey = 'trafficChartPrefs';
        this.DEBUG = false;
        this.retryCount = 2;
        this.timeoutMs = 10000;
        this.chartLib = null; // Lazy load control

        this.baseConfig = {
            responsive: {
                enable: true,
                mobileBreakpoint: 640,
                tickLimits: { mobile: 6, desktop: 14 },
                fontSizes: { 
                    x: { mobile: 9, desktop: 11 }, 
                    y: { mobile: 9, desktop: 11 }, 
                    legend: { mobile: 10, desktop: 12 } 
                }
            },
            cache: { enable: true, ttlMs: 120000 },
            theme: { mode: 'auto' },
            refresh: { enable: false, intervalMs: 15000 },
            compact: false, // Flag indicating the new compact mode
            callbacks: {
                onDataFetched: null,
                onChartLoaded: null,
                onError: null,
                onModalOpened: null, // New callback hook
                onModalClosed: null  // New callback hook
            }
        };

    const savedPrefs = this._loadPrefs();
    let persistedPeriod = null;
    if (savedPrefs && typeof savedPrefs.period !== 'undefined') {
        const legacy = savedPrefs.period;
        if (typeof legacy === 'string') {
            if (/^\d+h$/.test(legacy)) {
                persistedPeriod = parseInt(legacy.replace('h',''), 10);
            } else if (/^\d+d$/.test(legacy)) {
                persistedPeriod = parseInt(legacy.replace('d',''), 10) * 24;
            } else if (!isNaN(parseInt(legacy,10))) {
                persistedPeriod = parseInt(legacy,10);
            }
        } else if (typeof legacy === 'number') {
            persistedPeriod = legacy;
        }
    }
    this.config = this._mergeDeep(this.baseConfig, savedPrefs || {});
    this.config.period = persistedPeriod || 1;

        this._onResize = this._onResize.bind(this);
    }

    /*----------------------------------------------------------
      Core API
    ----------------------------------------------------------*/

    configure(partialConfig = {}) {
        this.config = this._mergeDeep(this.config, partialConfig);
        this._savePrefs();
    }

    setTheme(mode = 'auto', { instanceId = null } = {}) {
        if (instanceId && this.instances.has(instanceId)) {
            // Theme scoped to a specific instance
            this.instances.get(instanceId).theme = mode;
            this._refreshInstance(instanceId);
        } else {
            // Global theme settings
            this.config.theme.mode = mode;
            this._savePrefs();
            this._refreshAllCharts();
        }
    }

    startAutoRefresh(intervalMs) {
        if (intervalMs) this.config.refresh.intervalMs = intervalMs;
        this.config.refresh.enable = true;
        this._savePrefs();
        this._refreshAllCharts();
    }

    stopAutoRefresh() {
        this.config.refresh.enable = false;
        this._savePrefs();
        this._refreshAllCharts();
    }

    /*----------------------------------------------------------
      Show port chart (lazy load)
    ----------------------------------------------------------*/

    async showPortTrafficChart(portId, portName, deviceName, { compact = null } = {}) {
        // Load Chart.js and plugins on demand
        await this._ensureChartLibrary();

        const modalId = `trafficModal-${portId}`;
        let modal = document.getElementById(modalId);

        // Usa compact do config se not especificado
        const useCompact = compact !== null ? compact : this.config.compact;

        if (!modal) {
            modal = this._createModalInstance(modalId, portName, deviceName, useCompact);
        }

        const instance = {
            id: portId,
            modal,
            chart: null,
            refreshTimer: null,
            period: (this._loadPrefs().period || this.defaultPeriod), // horas
            lastData: null,
            lastTimestamp: null, // Track incremental refresh state
            portName,
            deviceName,
            theme: this.config.theme.mode,
            compact: useCompact
        };

        this.instances.set(portId, instance);
        this._emit('onModalOpened', instance);
        
        await this._loadChartData(instance);
    }

    /*----------------------------------------------------------
      Data fetch and incremental rendering
    ----------------------------------------------------------*/

    async _loadChartData(instance) {
        const { modal, id: portId, period, lastTimestamp } = instance;
        const canvas = modal.querySelector('canvas');
        const skeleton = modal.querySelector('.trafficSkeleton');
        const footer = modal.querySelector('.trafficFooter');
        const lastUpdateEl = modal.querySelector('.trafficLastUpdate');
        const errorEl = modal.querySelector('.trafficError');

        this._showLoading(modal, skeleton, errorEl);

        try {
            // ---- Local cache with incremental support ----
            const cacheKey = `traffic:${portId}:${period}h`;
            let payload = null;
            
            if (this.config.cache.enable && !lastTimestamp) {
                // Only use cache for the initial load, not for incremental updates
                const cached = this._readCache(cacheKey);
                if (cached) payload = cached;
            }

            // ---- Busca na API ----
            if (!payload) {
                let endpoint = `/api/v1/inventory/ports/${portId}/traffic/?period=${period}h`;
                
                // Adiciona parameter incremental se available
                if (lastTimestamp) {
                    endpoint += `&since=${lastTimestamp}`;
                }

                const response = await this._fetchWithRetry(endpoint);
                payload = await response.json();

                if (!payload || payload.error) {
                    throw new Error(payload?.error || 'Error loading data from the API');
                }

                // Cache only for full refreshes (non-incremental)
                if (this.config.cache.enable && !lastTimestamp) {
                    this._writeCache(cacheKey, payload);
                }
            }

            this._emit('onDataFetched', payload);

            const hasIn = payload.in.history?.length > 0;
            const hasOut = payload.out.history?.length > 0;

            if (!hasIn && !hasOut) {
                let errorMsg = 'No traffic data available for this port.';
                if (!payload.in.configured && !payload.out.configured) {
                    errorMsg += '\n\nX Traffic items are not configured.';
                } else if (!payload.in.configured) {
                    errorMsg += '\n\nWarning Inbound item not configured.';
                } else if (!payload.out.configured) {
                    errorMsg += '\n\nWarning Outbound item not configured.';
                }
                throw new Error(errorMsg);
            }

            // ---- Processamento de data incrementais ----
            if (lastTimestamp && instance.lastData) {
                // Merge incremental: adiciona novos data aos existentes
                if (payload.in.history) {
                    instance.lastData.in.history.push(...payload.in.history);
                }
                if (payload.out.history) {
                    instance.lastData.out.history.push(...payload.out.history);
                }
            } else {
                // Carga inicial
                instance.lastData = payload;
            }

            // Update latest timestamp for the next incremental fetch
            const allTimestamps = [
                ...(payload.in.history || []).map(p => p.timestamp),
                ...(payload.out.history || []).map(p => p.timestamp)
            ];
            if (allTimestamps.length > 0) {
                instance.lastTimestamp = Math.max(...allTimestamps);
            }

            const chartData = this._prepareChartData(instance.lastData);
            const datasets = this._createDatasets(chartData, hasIn, hasOut, canvas, instance.theme);

            // Destroys chart anterior se existir
            if (instance.chart) {
                instance.chart.destroy();
                instance.chart = null;
            }

            // Cria novo chart
            instance.chart = this._createTrafficChart(canvas, chartData, datasets, instance.theme);
            
            // Add controls to the chart
            this._addChartControls(canvas, instance);
            
            // Update UI
            this._renderStatsFooter(footer, datasets);
            
            const lastTs = chartData.timestamps.at(-1);
            if (lastTs) {
                lastUpdateEl.textContent = `Updated: ${lastTs.toLocaleTimeString('en-US')}`;
            }

            this._showChart(modal, skeleton, errorEl);
            this._emit('onChartLoaded', { chart: instance.chart, datasets });

            // Auto-refresh
            if (this.config.refresh.enable) {
                this._scheduleInstanceRefresh(instance);
            }

        } catch (err) {
            this._showError(modal, skeleton, errorEl, err.message);
            this._emit('onError', err);
            console.error('Traffic chart error:', err);
        }
    }

    /*----------------------------------------------------------
      Fetch with retry
    ----------------------------------------------------------*/

    async _fetchWithRetry(url) {
        // Detect period in the URL (pattern period=<num>h) to scale the timeout
        let effectiveTimeout = this.timeoutMs;
        try {
            const m = url.match(/period=(\d+)h/i);
            if (m) {
                const hours = parseInt(m[1], 10);
                if (hours >= 720) { // 30 days
                    effectiveTimeout = 180000; // 3 minutes
                } else if (hours >= 168) { // 7+ dias
                    effectiveTimeout = Math.max(effectiveTimeout, 30000); // 30s
                } else if (hours >= 24) { // >= 24h
                    effectiveTimeout = Math.max(effectiveTimeout, 20000); // 20s
                }
            }
        } catch (_) { /* ignore parse errors */ }

        for (let i = 0; i <= this.retryCount; i++) {
            const controller = new AbortController();
            const timeout = setTimeout(() => controller.abort(), effectiveTimeout);

            try {
                const response = await fetch(url, { signal: controller.signal });
                clearTimeout(timeout);
                
                if (response.ok) return response;
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            } catch (err) {
                clearTimeout(timeout);
                
                if (this.DEBUG) {
                    console.warn(`Tentativa ${i + 1}/${this.retryCount + 1} falhou:`, err);
                }
                
                if (i === this.retryCount) throw err;
                await new Promise(r => setTimeout(r, 1000 * (i + 1)));
            }
        }
    }

    /*----------------------------------------------------------
      Settings CHART.JS LAZY LOADING
    ----------------------------------------------------------*/

    async _ensureChartLibrary() {
        if (this.chartLib && this.chartLib.Chart) return;

        // Se already existe Chart global (carregado via tag <script>), reutiliza
        if (window.Chart) {
            this.chartLib = { Chart: window.Chart };
            return;
        }

        const loadScript = (src) => new Promise((resolve, reject) => {
            const existing = document.querySelector(`script[src="${src}"]`);
            if (existing && existing.dataset.loaded === 'true') return resolve();
            const s = existing || document.createElement('script');
            s.src = src;
            s.async = true;
            s.onload = () => { s.dataset.loaded = 'true'; resolve(); };
            s.onerror = reject;
            if (!existing) document.head.appendChild(s);
        });

        try {
            // Primeiro tenta dynamic import (navegadores modernos)
            try {
                this.chartLib = await import('https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js');
            } catch (dynErr) {
                console.warn('Dynamic import failed, falling back to a Chart.js script tag', dynErr);
                await loadScript('https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js');
                this.chartLib = { Chart: window.Chart };
            }
            // Plugin zoom
            if (!window.chartjsPluginZoom) {
                try {
                    await import('https://cdn.jsdelivr.net/npm/chartjs-plugin-zoom@2.0.1/dist/chartjs-plugin-zoom.min.js');
                } catch (dynZoomErr) {
                    console.warn('Dynamic import for the zoom plugin failed, falling back to a script tag');
                    await loadScript('https://cdn.jsdelivr.net/npm/chartjs-plugin-zoom@2.0.1/dist/chartjs-plugin-zoom.min.js');
                }
            }
            console.info('Chart.js + Zoom plugin ready');
        } catch (e) {
            console.error('Failed to load Chart.js:', e);
            throw e;
        }
    }

    /*----------------------------------------------------------
      Modal creation with compact mode
    ----------------------------------------------------------*/

    _createModalInstance(id, portName, deviceName, compact = false) {
        const modal = document.createElement('div');
        modal.id = id;
        modal.className = 'trafficModal fixed inset-0 bg-black/60 flex items-center justify-center z-50';
        
        const heightClass = compact ? 'h-60' : 'h-96';
        const compactBorder = compact ? 'border border-gray-300 dark:border-gray-700' : '';
        
        modal.innerHTML = `
            <div class="bg-white dark:bg-gray-900 rounded-lg shadow-xl w-11/12 md:w-4/5 lg:w-3/5 xl:w-2/3 relative ${compactBorder}">
                <!-- Header -->
                <div class="flex justify-between items-center px-6 py-4 border-b border-gray-200 dark:border-gray-700">
                    <h2 class="text-lg font-semibold text-gray-800 dark:text-gray-200">
                        Traffic - ${deviceName} :: ${portName}
                    </h2>
                    <div class="flex items-center gap-3">
                        <select class="trafficPeriod text-xs border rounded px-3 py-2 bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500">
                            ${this.availablePeriods.map(h => {
                                const label = h >= 24 ? (h % 24 === 0 ? `${h/24}d` : `${h}h`) : `${h}h`;
                                return `<option value="${h}">Last ${label}</option>`;
                            }).join('')}
                        </select>
                        <button class="trafficClose text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 text-lg transition-colors" title="Close">
                            x
                        </button>
                    </div>
                </div>

                <!-- Error Message -->
                <div class="trafficError hidden px-6 py-3 bg-red-50 dark:bg-red-900/20 border-b border-red-200 dark:border-red-800">
                    <p class="text-red-700 dark:text-red-300 text-sm"></p>
                </div>

                <!-- Chart Area -->
                <div class="relative ${heightClass} p-4 overflow-hidden">
                    <!-- Skeleton Loader -->
                    <div class="trafficSkeleton absolute inset-4 bg-gradient-to-r from-gray-200 via-gray-100 to-gray-200 dark:from-gray-700 dark:via-gray-800 dark:to-gray-700 animate-pulse rounded-lg"></div>
                    
                    <!-- Chart Canvas -->
                    <canvas class="w-full h-full"></canvas>
                </div>

                <!-- Footer (oculto no modo compacto) -->
                <div class="trafficFooter px-6 py-3 border-t border-gray-200 dark:border-gray-700 ${compact ? 'hidden' : ''}"></div>
                
                <!-- Last Update -->
                <div class="trafficLastUpdate text-right text-xs text-gray-500 dark:text-gray-400 px-6 pb-3 ${compact ? 'hidden' : ''}"></div>
            </div>
        `;
        
        document.body.appendChild(modal);
        this._attachModalEvents(modal, id);
        return modal;
    }

    _addExportButtons(container, instance) {
        if (container.querySelector('.export-buttons')) return;

        const wrapper = document.createElement('div');
        wrapper.className = 'export-buttons absolute top-1 right-1 flex gap-2';
        wrapper.innerHTML = `
            <button class="export-png-btn px-3 py-1.5 bg-gray-700/80 hover:bg-gray-600 text-gray-300 rounded border border-gray-600 text-xs font-medium transition-colors" title="Export as PNG">
                PNG
            </button>
            <button class="export-csv-btn px-3 py-1.5 bg-gray-700/80 hover:bg-gray-600 text-gray-300 rounded border border-gray-600 text-xs font-medium transition-colors" title="Export as CSV">
                CSV
            </button>
        `;
        
        container.appendChild(wrapper);

        // PNG Export
        wrapper.querySelector('.export-png-btn').addEventListener('click', () => {
            if (instance.chart) {
                const link = document.createElement('a');
                link.href = instance.chart.toBase64Image();
                link.download = `traffic-${instance.portName}-${new Date().toISOString().split('T')[0]}.png`;
                link.click();
            }
        });

        // CSV Export
        wrapper.querySelector('.export-csv-btn').addEventListener('click', () => {
            if (instance.chart && instance.lastData) {
                const csv = this._exportToCSV(instance.chart, instance.lastData);
                const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
                const link = document.createElement('a');
                link.href = URL.createObjectURL(blob);
                link.download = `traffic-${instance.portName}-${new Date().toISOString().split('T')[0]}.csv`;
                link.click();
                URL.revokeObjectURL(link.href);
            }
        });
    }

    _attachModalEvents(modal, id) {
        // Close modal
        modal.querySelector('.trafficClose').addEventListener('click', () => {
            this._closeModalInstance(id);
        });

        // Change period
        modal.querySelector('.trafficPeriod').addEventListener('change', (e) => {
            const instanceId = id.replace('trafficModal-', '');
            const instance = this.instances.get(instanceId);
            if (instance) {
                instance.period = parseInt(e.target.value,10);
                instance.lastTimestamp = null; // Reset incremental window when the period changes
                this._savePrefs({ period: e.target.value });
                this._loadChartData(instance);
            }
        });

        // Close when the backdrop is clicked
        modal.addEventListener('click', (e) => {
            if (e.target === modal) this._closeModalInstance(id);
        });

        // Close with ESC
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this._closeModalInstance(id);
            }
        });
    }

    _closeModalInstance(id) {
        const instanceId = id.replace('trafficModal-', '');
        const instance = this.instances.get(instanceId);
        
        if (!instance) return;

        // Emite evento antes de fechar
        this._emit('onModalClosed', { instanceId, instance });

        // Cleanup
        if (instance.chart) instance.chart.destroy();
        if (instance.refreshTimer) clearTimeout(instance.refreshTimer);
        
        this.instances.delete(instanceId);

        const modal = document.getElementById(id);
        if (modal) modal.remove();
    }

    /*----------------------------------------------------------
      UI controls: loading, error, chart
    ----------------------------------------------------------*/

    _showLoading(modal, skeleton, errorEl) {
        if (errorEl) errorEl.classList.add('hidden');
        if (skeleton) skeleton.classList.remove('hidden');
        modal.querySelector('canvas')?.classList.add('hidden');
    }

    _showChart(modal, skeleton, errorEl) {
        if (errorEl) errorEl.classList.add('hidden');
        if (skeleton) skeleton.classList.add('hidden');
        modal.querySelector('canvas')?.classList.remove('hidden');
    }

    _showError(modal, skeleton, errorEl, message) {
        if (skeleton) skeleton.classList.add('hidden');
        modal.querySelector('canvas')?.classList.add('hidden');
        
        if (errorEl) {
            errorEl.classList.remove('hidden');
            const errorP = errorEl.querySelector('p');
            if (errorP) errorP.textContent = message;
        }
    }

    /*----------------------------------------------------------
      Chart creation with controls
    ----------------------------------------------------------*/

    _createTrafficChart(canvas, chartData, datasets, theme) {
        const dark = this._resolveTheme(theme);
        const grafanaColors = {
            grid: dark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.08)',
            text: dark ? '#d0d0d0' : '#303030',
            tooltipBg: dark ? 'rgba(25,25,35,0.95)' : 'rgba(255,255,255,0.95)',
            tooltipBorder: dark ? 'rgba(255,255,255,0.15)' : 'rgba(0,0,0,0.1)'
        };

        return new this.chartLib.Chart(canvas.getContext('2d'), {
            type: 'line',
            data: { labels: chartData.labels, datasets },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    mode: 'index',
                    intersect: false,
                    axis: 'x'
                },
                plugins: {
                    legend: {
                        position: 'bottom',
                        align: 'center',
                        labels: {
                            color: grafanaColors.text,
                            usePointStyle: true,
                            pointStyle: 'circle',
                            boxWidth: 8,
                            boxHeight: 8,
                            font: {
                                size: this._legendFontSize(),
                                family: "'Inter', 'Helvetica Neue', sans-serif",
                                weight: '400'
                            },
                            padding: 15
                        }
                    },
                    tooltip: {
                        backgroundColor: grafanaColors.tooltipBg,
                        titleColor: dark ? '#ffffff' : '#000000',
                        bodyColor: dark ? '#d0d0d0' : '#333333',
                        borderColor: grafanaColors.tooltipBorder,
                        borderWidth: 1,
                        padding: 12,
                        displayColors: true,
                        usePointStyle: true,
                        titleFont: {
                            size: 12,
                            family: "'Inter', sans-serif",
                            weight: '500'
                        },
                        bodyFont: {
                            size: this._axisFontSize(),
                            family: "'Roboto Mono', monospace"
                        },
                        callbacks: {
                            title: (context) => {
                                const index = context[0].dataIndex;
                                return chartData.timestamps[index].toLocaleString('en-US', {
                                    day: '2-digit',
                                    month: '2-digit',
                                    year: 'numeric',
                                    hour: '2-digit',
                                    minute: '2-digit',
                                    second: '2-digit'
                                });
                            },
                            label: (context) => {
                                return `${context.dataset.label}: ${this._formatTrafficValue(context.parsed.y)}`;
                            }
                        }
                    },
                    zoom: {
                        pan: {
                            enabled: true,
                            mode: 'x',
                            modifierKey: null
                        },
                        zoom: {
                            wheel: {
                                enabled: true,
                                speed: 0.05,
                                modifierKey: null
                            },
                            pinch: {
                                enabled: true
                            },
                            mode: 'x'
                        },
                        limits: {
                            x: { min: 'original', max: 'original' }
                        }
                    }
                },
                scales: {
                    x: {
                        type: 'category',
                        ticks: {
                            color: grafanaColors.text,
                            font: {
                                size: this._axisFontSize(),
                                family: "'Roboto Mono', monospace",
                                weight: '400'
                            },
                            maxRotation: 0,
                            minRotation: 0,
                            autoSkip: true,
                            autoSkipPadding: 20,
                            maxTicksLimit: this._maxTicksLimit(),
                            padding: 8
                        },
                        grid: {
                            color: grafanaColors.grid,
                            lineWidth: 1,
                            drawTicks: false,
                            drawBorder: false
                        },
                        border: { display: false }
                    },
                    y: {
                        beginAtZero: true,
                        type: 'linear',
                        ticks: {
                            color: grafanaColors.text,
                            font: {
                                size: this._axisFontSize(),
                                family: "'Roboto Mono', monospace",
                                weight: '400'
                            },
                            padding: 8,
                            callback: (value) => this._formatYAxisValue(value)
                        },
                        grid: {
                            color: grafanaColors.grid,
                            lineWidth: 1,
                            drawTicks: false,
                            drawBorder: false
                        },
                        border: { display: false }
                    }
                },
                elements: {
                    line: {
                        tension: 0.1
                    },
                    point: {
                        radius: 0,
                        hoverRadius: 3,
                        hoverBorderWidth: 2,
                        hoverBackgroundColor: '#ffffff'
                    }
                },
                animation: {
                    duration: 300,
                    easing: 'easeOutQuart'
                }
            }
        });
    }

    _addChartControls(canvas, instance) {
        const container = canvas.parentElement;
        
        // Button Reset Zoom
        this._addResetZoomButton(container, instance);
        
        // Buttons Export (apenas no modo normal)
        if (!instance.compact) {
            this._addExportButtons(container, instance);
        }
    }

    /*----------------------------------------------------------
      Chart controls
    ----------------------------------------------------------*/

    _addResetZoomButton(container, instance) {
        let btn = container.querySelector('.reset-zoom-btn');
        const canvasEl = container.querySelector('canvas');

        if (!btn) {
            btn = document.createElement('button');
            btn.className = 'reset-zoom-btn';
            btn.innerHTML = 'Reset Zoom';
            Object.assign(btn.style, {
                position: 'absolute',
                top: '10px',
                right: '10px',
                padding: '6px 12px',
                background: 'rgba(40, 40, 50, 0.9)',
                color: '#8f9bb3',
                border: '1px solid rgba(255, 255, 255, 0.1)',
                borderRadius: '3px',
                fontSize: '11px',
                fontWeight: '500',
                cursor: 'pointer',
                zIndex: 1000,
                transition: 'all 0.2s ease',
                display: 'none',
                fontFamily: "'Inter', sans-serif"
            });
            btn.addEventListener('click', () => {
                if (instance.chart && instance.chart.resetZoom) {
                    instance.chart.resetZoom();
                    btn.style.display = 'none';
                }
            });
            container.style.position = 'relative';
            container.appendChild(btn);
        }

        if (canvasEl) {
            canvasEl.addEventListener('wheel', () => { btn.style.display = 'block'; }, { passive: true });
        }
    }

    _exportToCSV(chart, rawData) {
        const headers = ['Timestamp', 'Data/Hora', 'Entrada (bps)', 'Outbound (bps)'];
        const rows = [headers];
        
        // Map timestamps to values
        const inMap = {};
        const outMap = {};
        
        (rawData.in.history || []).forEach(point => {
            inMap[point.timestamp] = point.value;
        });
        
        (rawData.out.history || []).forEach(point => {
            outMap[point.timestamp] = point.value;
        });
        
        // Coletar todos os timestamps unique e ordenar
        const allTimestamps = [...new Set([
            ...(rawData.in.history || []).map(p => p.timestamp),
            ...(rawData.out.history || []).map(p => p.timestamp)
        ])].sort();
        
        // Criar linhas CSV
        allTimestamps.forEach(timestamp => {
            const date = new Date(timestamp * 1000);
            const row = [
                timestamp,
                date.toLocaleString('en-US'),
                inMap[timestamp] || '0',
                outMap[timestamp] || '0'
            ];
            rows.push(row);
        });
        
        return rows.map(row => 
            row.map(field => `"${String(field).replace(/"/g, '""')}"`)
            .join(',')
        ).join('\n');
    }

    /*----------------------------------------------------------
      Data preparation and datasets
    ----------------------------------------------------------*/

    _prepareChartData(data) {
        const allTimestamps = new Set();
        const inMap = {}, outMap = {};

        (data.in.history || []).forEach(point => {
            inMap[point.timestamp] = point.value;
            allTimestamps.add(point.timestamp);
        });

        (data.out.history || []).forEach(point => {
            outMap[point.timestamp] = point.value;
            allTimestamps.add(point.timestamp);
        });

        const sortedTimestamps = Array.from(allTimestamps).sort((a, b) => a - b);
        
        const labels = sortedTimestamps.map(ts => 
            new Date(ts * 1000).toLocaleTimeString('en-US', {
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit'
            })
        );
        
        const timestamps = sortedTimestamps.map(ts => new Date(ts * 1000));
        const dataIn = sortedTimestamps.map(ts => inMap[ts] || 0);
        const dataOut = sortedTimestamps.map(ts => outMap[ts] || 0);

        return { labels, timestamps, dataIn, dataOut };
    }

    _createDatasets(chartData, hasIn, hasOut, canvas, theme) {
        const datasets = [];
        const ctx = canvas.getContext('2d');
        const darkMode = this._resolveTheme(theme);

        if (hasIn) {
            const stats = this._calculateStats(chartData.dataIn);
            const gradient = ctx.createLinearGradient(0, 0, 0, canvas.height);
            gradient.addColorStop(0, darkMode ? 'rgba(51,181,229,0.6)' : 'rgba(51,181,229,0.5)');
            gradient.addColorStop(1, 'rgba(51,181,229,0.0)');

            datasets.push({
                label: 'Entrada (IN)',
                data: chartData.dataIn,
                borderColor: '#33b5e5',
                backgroundColor: gradient,
                fill: true,
                borderWidth: 1.5,
                pointRadius: 0,
                pointHoverRadius: 3,
                tension: 0.1,
                stats
            });
        }

        if (hasOut) {
            const stats = this._calculateStats(chartData.dataOut);
            const gradient = ctx.createLinearGradient(0, 0, 0, canvas.height);
            gradient.addColorStop(0, darkMode ? 'rgba(0,230,118,0.5)' : 'rgba(0,230,118,0.4)');
            gradient.addColorStop(1, 'rgba(0,230,118,0.0)');

            datasets.push({
                label: 'Outbound (OUT)',
                data: chartData.dataOut,
                borderColor: '#00e676',
                backgroundColor: gradient,
                fill: true,
                borderWidth: 1.5,
                pointRadius: 0,
                pointHoverRadius: 3,
                tension: 0.1,
                stats
            });
        }

        return datasets;
    }

    /*----------------------------------------------------------
      Full statistics
    ----------------------------------------------------------*/

    _renderStatsFooter(footer, datasets) {
        const statsHTML = datasets.map(dataset => {
            const { stats, label } = dataset;
            if (!stats) return '';

            return `
                <div class="flex justify-between items-center text-xs text-gray-600 dark:text-gray-400 py-1">
                    <span class="font-medium">${label}:</span>
                    <span class="text-xs">
                        Average: <strong>${this._formatTrafficValue(stats.mean)}</strong> | 
                        P95: <strong>${this._formatTrafficValue(stats.p95)}</strong> | 
                        Max: <strong>${this._formatTrafficValue(stats.max)}</strong> |
                        Samples: <strong>${stats.samples}</strong>
                    </span>
                </div>
            `;
        }).join('');

        footer.innerHTML = `
            <div class="mt-2 pt-3 border-t border-gray-200 dark:border-gray-700">
                ${statsHTML}
            </div>
        `;
    }

    _calculateStats(data) {
        const valid = data.filter(v => v > 0);
        if (!valid.length) return null;

        const sum = valid.reduce((a, b) => a + b, 0);
        const mean = sum / valid.length;
        const sorted = [...valid].sort((a, b) => a - b);
        const p95Index = Math.floor(0.95 * sorted.length);
        const p95 = sorted[p95Index];

        return { 
            mean, 
            p95, 
            max: Math.max(...valid), 
            min: Math.min(...valid), 
            samples: valid.length 
        };
    }

    /*----------------------------------------------------------
      Settings UTILITIES E FORMATTING
    ----------------------------------------------------------*/

    _formatTrafficValue(value) {
        if (value >= 1e9) return (value / 1e9).toFixed(2) + ' Gbps';
        if (value >= 1e6) return (value / 1e6).toFixed(2) + ' Mbps';
        if (value >= 1e3) return (value / 1e3).toFixed(2) + ' Kbps';
        return value.toFixed(2) + ' bps';
    }

    _formatYAxisValue(value) {
        if (value === 0) return '0';
        if (value >= 1e9) return (value / 1e9).toFixed(1) + 'G';
        if (value >= 1e6) return (value / 1e6).toFixed(1) + 'M';
        if (value >= 1e3) return (value / 1e3).toFixed(1) + 'K';
        return value.toFixed(1);
    }

    _resolveTheme(mode) {
        if (mode === 'dark') return true;
        if (mode === 'light') return false;
        return window.matchMedia('(prefers-color-scheme: dark)').matches;
    }

    /*----------------------------------------------------------
      Cache and persistence
    ----------------------------------------------------------*/

    _readCache(key) {
        try {
            const raw = localStorage.getItem(key);
            if (!raw) return null;
            
            const { ts, ttl, data } = JSON.parse(raw);
            if (!ts || !ttl || !data) return null;
            
            if (Date.now() - ts > ttl) {
                localStorage.removeItem(key);
                return null;
            }
            
            return data;
        } catch (e) {
            if (this.DEBUG) console.warn('Error reading cache:', e);
            return null;
        }
    }

    _writeCache(key, data) {
        try {
            const payload = JSON.stringify({ 
                ts: Date.now(), 
                ttl: this.config.cache.ttlMs, 
                data 
            });
            localStorage.setItem(key, payload);
        } catch (e) {
            if (this.DEBUG) console.warn('Failed to write cache:', e);
        }
    }

    _loadPrefs() {
        try {
            const prefs = localStorage.getItem(this.localStorageKey);
            return prefs ? JSON.parse(prefs) : {};
        } catch {
            return {};
        }
    }

    _savePrefs(extra = {}) {
        try {
            const prefs = { ...this.config, ...extra };
            localStorage.setItem(this.localStorageKey, JSON.stringify(prefs));
        } catch (err) {
            if (this.DEBUG) console.warn('Error saving preferences:', err);
        }
    }

    /*----------------------------------------------------------
      Auto-refresh per instance
    ----------------------------------------------------------*/

    _scheduleInstanceRefresh(instance) {
        if (!this.config.refresh.enable) return;
        
        if (instance.refreshTimer) {
            clearTimeout(instance.refreshTimer);
        }
        
        instance.refreshTimer = setTimeout(() => {
            this._loadChartData(instance);
        }, this.config.refresh.intervalMs);
    }

    _refreshInstance(instanceId) {
        const instance = this.instances.get(instanceId);
        if (instance) {
            this._loadChartData(instance);
        }
    }

    _refreshAllCharts() {
        for (const [id, instance] of this.instances.entries()) {
            this._loadChartData(instance);
        }
    }

    /*----------------------------------------------------------
      Responsiveness helpers
    ----------------------------------------------------------*/

    _onResize() {
        // Implement if additional responsive behaviour is needed
    }

    _isMobile() {
        return window.innerWidth <= this.config.responsive.mobileBreakpoint;
    }

    _maxTicksLimit() {
        const { tickLimits } = this.config.responsive;
        return this._isMobile() ? tickLimits.mobile : tickLimits.desktop;
    }

    _axisFontSize() {
        const { x } = this.config.responsive.fontSizes;
        return this._isMobile() ? x.mobile : x.desktop;
    }

    _legendFontSize() {
        const { legend } = this.config.responsive.fontSizes;
        return this._isMobile() ? legend.mobile : legend.desktop;
    }

    _mergeDeep(target, source) {
        const out = { ...target };
        
        for (const key of Object.keys(source)) {
            if (source[key] && typeof source[key] === 'object' && !Array.isArray(source[key])) {
                out[key] = this._mergeDeep(target[key] || {}, source[key]);
            } else {
                out[key] = source[key];
            }
        }
        
        return out;
    }

    _emit(callbackName, payload) {
        try {
            const callback = this.config.callbacks?.[callbackName];
            if (typeof callback === 'function') callback(payload);
        } catch (e) {
            if (this.DEBUG) console.warn(`Callback ${callbackName} falhou:`, e);
        }
    }
}

// Singleton global
const trafficChartManager = new TrafficChartManager();

if (typeof window !== "undefined") {
    window.trafficChartManager = trafficChartManager;
}

// Global helper used in dashboard.js to reattach listeners after dynamically loading markers
window.attachTrafficButtonListeners = function attachTrafficButtonListeners() {
    // Delegation evita multiple binds em elementos existentes
    if (!window.__trafficBtnDelegation) {
        document.addEventListener('click', (e) => {
            const btn = e.target.closest('.traffic-btn');
            if (!btn) return;
            e.stopPropagation();
            trafficChartManager.showPortTrafficChart(
                btn.getAttribute('data-port-id'),
                btn.getAttribute('data-port-name'),
                btn.getAttribute('data-device-name')
            );
        });
        window.__trafficBtnDelegation = true;
    }
};

// Auto-initialization dos event listeners
// Inicializa delegation (suporta elementos adicionados depois)
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => window.attachTrafficButtonListeners());
} else {
    window.attachTrafficButtonListeners();
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = { TrafficChartManager, trafficChartManager };
}
