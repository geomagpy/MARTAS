// plotws.js - MARCOS WebSocket Live Plotter (Dark Mode & Interactive Controls)

(function () {
    const serveraddr = location.host ? location.host.split(':')[0] : 'localhost';
    const wsUrl = `ws://${serveraddr}:5000/`;
    const sensorblacklist = ['', 'none'];

    let wsconnection = null;
    let isPaused = false;
    let chartHeight = 180;
    let timeWindowSeconds = 180;

    // Stores all active signals: signals["SENSORID#0"] = { head, chart, timeSeries, card, canvas, checkbox, valueEl, visible }
    const signals = {};
    const sensorGroups = {};

    // DOM Elements
    const maindiv = document.getElementById('maindiv');
    const sensorListEl = document.getElementById('sensor-list');
    const debugEl = document.getElementById('debug');
    const wsStatusBadge = document.getElementById('ws-status');
    const wsStatusText = document.getElementById('ws-status-text');
    const serverInfoEl = document.getElementById('server-info');

    const timeWindowSelect = document.getElementById('timeWindowSelect');
    const heightSlider = document.getElementById('heightSlider');
    const heightValueEl = document.getElementById('heightValue');
    const layoutSelect = document.getElementById('layoutSelect');
    const yPaddingSelect = document.getElementById('yPaddingSelect');
    const interpolationSelect = document.getElementById('interpolationSelect');
    const pauseBtn = document.getElementById('pauseBtn');
    const selectAllBtn = document.getElementById('selectAllBtn');
    const selectNoneBtn = document.getElementById('selectNoneBtn');

    serverInfoEl.textContent = `WebSocket: ${wsUrl}`;

    /**
     * Updates millisPerPixel and grid intervals based on current canvas width and selected time window
     */
    function updateTimeScale() {
        timeWindowSeconds = Number(timeWindowSelect.value);
        const totalMs = timeWindowSeconds * 1000;

        let millisPerLine = 10000;
        if (timeWindowSeconds <= 30) millisPerLine = 5000;
        else if (timeWindowSeconds <= 60) millisPerLine = 10000;
        else if (timeWindowSeconds <= 300) millisPerLine = 30000;
        else if (timeWindowSeconds <= 900) millisPerLine = 120000;
        else if (timeWindowSeconds <= 3600) millisPerLine = 600000;     // 10 min
        else if (timeWindowSeconds <= 43200) millisPerLine = 3600000;   // 1 h
        else millisPerLine = 7200000;                                   // 2 h

        Object.values(signals).forEach(sig => {
            const width = sig.canvas.clientWidth || sig.canvas.width || 800;
            sig.chart.options.millisPerPixel = totalMs / width;
            sig.chart.options.grid.millisPerLine = millisPerLine;
        });
    }

    /**
     * Matches internal canvas pixel resolution to its rendered CSS dimensions
     */
    function resizeCanvases() {
        Object.values(signals).forEach(sig => {
            if (!sig.visible) return;
            const rect = sig.canvas.parentElement.getBoundingClientRect();
            if (rect.width > 0) {
                sig.canvas.width = Math.floor(rect.width);
                sig.canvas.height = chartHeight;
            }
        });
        updateTimeScale();
    }

    /**
     * Adds a sensor channel toggle checkbox to the sidebar
     */
    function addSidebarItem(head, signalid) {
        if (Object.keys(sensorGroups).length === 0) {
            sensorListEl.innerHTML = '';
        }

        if (!sensorGroups[head.sensorid]) {
            const groupDiv = document.createElement('div');
            groupDiv.className = 'sensor-group';

            const titleDiv = document.createElement('div');
            titleDiv.className = 'sensor-group-title';
            titleDiv.textContent = head.sensorid;
            groupDiv.appendChild(titleDiv);

            sensorListEl.appendChild(groupDiv);
            sensorGroups[head.sensorid] = groupDiv;
        }

        const color = signalColors[head.nr % signalColors.length];
        const label = document.createElement('label');
        label.className = 'signal-item';

        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.checked = true;

        const colorDot = document.createElement('span');
        colorDot.className = 'color-indicator';
        colorDot.style.backgroundColor = color;

        const textSpan = document.createElement('span');
        const unitStr = head.unit ? ` [${head.unit}]` : '';
        textSpan.textContent = `${head.elem} (${head.key})${unitStr}`;

        label.appendChild(checkbox);
        label.appendChild(colorDot);
        label.appendChild(textSpan);
        sensorGroups[head.sensorid].appendChild(label);

        checkbox.addEventListener('change', () => {
            setSignalVisibility(signalid, checkbox.checked);
        });

        return checkbox;
    }

    /**
     * Shows or hides a chart card
     */
    function setSignalVisibility(signalid, isVisible) {
        const sig = signals[signalid];
        if (!sig) return;
        sig.visible = isVisible;
        sig.checkbox.checked = isVisible;
        if (isVisible) {
            sig.card.classList.remove('hidden');
            resizeCanvases();
        } else {
            sig.card.classList.add('hidden');
        }
    }

    /**
     * Creates chart card, canvas, SmoothieChart, and TimeSeries for a signal
     */
    function createSignalChart(head, signalid) {
        const card = document.createElement('div');
        card.className = 'chart-card';

        const header = document.createElement('div');
        header.className = 'chart-header';

        const titleWrap = document.createElement('div');
        const titleSpan = document.createElement('span');
        titleSpan.className = 'chart-title';
        titleSpan.textContent = `${head.elem} (${head.key})`;

        const subSpan = document.createElement('span');
        subSpan.className = 'chart-subtitle';
        subSpan.textContent = `${head.sensorid}${head.unit ? ' • ' + head.unit : ''}`;

        titleWrap.appendChild(titleSpan);
        titleWrap.appendChild(subSpan);

        const valueEl = document.createElement('div');
        valueEl.className = 'chart-value';
        valueEl.textContent = '--';

        header.appendChild(titleWrap);
        header.appendChild(valueEl);

        const canvasWrapper = document.createElement('div');
        canvasWrapper.className = 'canvas-wrapper';

        const canvas = document.createElement('canvas');
        canvas.height = chartHeight;
        canvasWrapper.appendChild(canvas);

        card.appendChild(header);
        card.appendChild(canvasWrapper);
        maindiv.appendChild(card);

        const checkbox = addSidebarItem(head, signalid);

        // Initialize SmoothieChart (keep historical points in memory for up to 24h switching)
        const chart = new SmoothieChart(Object.assign({}, smoothiesettings, {
            maxDataSetLength: 0
        }));
        const timeSeries = new TimeSeries();
        chart.addTimeSeries(timeSeries, getTimeSeriesSettings(head.nr));
        chart.streamTo(canvas, streamtosettings.Delay);

        signals[signalid] = {
            head,
            chart,
            timeSeries,
            card,
            canvas,
            checkbox,
            valueEl,
            visible: true
        };

        requestAnimationFrame(() => resizeCanvases());
    }

    /**
     * Establishes WebSocket connection with automatic reconnect
     */
    function connectWebSocket() {
        wsconnection = new WebSocket(wsUrl);

        wsconnection.onopen = function () {
            wsStatusBadge.classList.add('connected');
            wsStatusText.textContent = 'Connected';
            debugEl.textContent = 'WebSocket connection active.';
        };

        wsconnection.onmessage = function (e) {
            if (e.data[0] === '#') {
                // Header / Metadata: # {"sensorid": ..., "nr": 0, "key": ..., "elem": ..., "unit": ...}
                try {
                    const jsonStr = e.data.substring(2);
                    const head = JSON.parse(jsonStr);
                    const signalid = `${head.sensorid}#${head.nr}`;

                    if (!signals[signalid] && !sensorblacklist.includes(head.sensorid)) {
                        createSignalChart(head, signalid);
                    }
                } catch (err) {
                    console.error('Error parsing metadata:', err, e.data);
                }
            } else {
                // Measurement data: sensorid: timestamp,val0,val1...
                const sepIdx = e.data.indexOf(': ');
                if (sepIdx === -1) return;

                const sensor = e.data.substring(0, sepIdx);
                if (sensorblacklist.includes(sensor)) return;

                const dataArr = e.data.substring(sepIdx + 2).split(',');
                const timestamp = Number(dataArr[0]);
                if (isNaN(timestamp)) return;

                for (let i = 0; i < dataArr.length - 1; i++) {
                    const signalid = `${sensor}#${i}`;
                    const sig = signals[signalid];
                    if (sig) {
                        const val = Number(dataArr[i + 1]);
                        if (!isNaN(val)) {
                            sig.timeSeries.append(timestamp, val);

                            if (!isPaused && sig.visible) {
                                const unitStr = sig.head.unit ? ` ${sig.head.unit}` : '';
                                sig.valueEl.textContent = `${dataArr[i + 1]}${unitStr}`;
                            }
                        }
                    }
                }

                if (!isPaused) {
                    const dt = new Date(timestamp);
                    debugEl.textContent = `Last packet (${sensor}): ${dt.toLocaleTimeString()} | Values: ${dataArr.slice(1).join(', ')}`;
                }
            }
        };

        wsconnection.onclose = function () {
            wsStatusBadge.classList.remove('connected');
            wsStatusText.textContent = 'Disconnected (Reconnecting...)';
            setTimeout(connectWebSocket, 3000);
        };

        wsconnection.onerror = function (error) {
            console.error('WebSocket error:', error);
            wsconnection.close();
        };
    }

    // --- UI Control Event Listeners ---

    timeWindowSelect.addEventListener('change', updateTimeScale);

    heightSlider.addEventListener('input', () => {
        chartHeight = Number(heightSlider.value);
        heightValueEl.textContent = `${chartHeight}px`;
        resizeCanvases();
    });

    layoutSelect.addEventListener('change', () => {
        if (layoutSelect.value === 'single') {
            maindiv.classList.add('single-column');
        } else {
            maindiv.classList.remove('single-column');
        }
        resizeCanvases();
    });

    yPaddingSelect.addEventListener('change', () => {
        currentYPadding = Number(yPaddingSelect.value);
    });

    interpolationSelect.addEventListener('change', () => {
        const mode = interpolationSelect.value;
        smoothiesettings.interpolation = mode;
        Object.values(signals).forEach(sig => {
            sig.chart.options.interpolation = mode;
        });
    });

    pauseBtn.addEventListener('click', () => {
        isPaused = !isPaused;
        pauseBtn.classList.toggle('active', isPaused);
        pauseBtn.textContent = isPaused ? '▶ Resume' : '⏸ Pause';

        Object.values(signals).forEach(sig => {
            if (isPaused) {
                sig.chart.stop();
            } else {
                sig.chart.start();
            }
        });
    });

    selectAllBtn.addEventListener('click', () => {
        Object.keys(signals).forEach(id => setSignalVisibility(id, true));
    });

    selectNoneBtn.addEventListener('click', () => {
        Object.keys(signals).forEach(id => setSignalVisibility(id, false));
    });

    window.addEventListener('resize', resizeCanvases);

    // Initialize
    connectWebSocket();
})();