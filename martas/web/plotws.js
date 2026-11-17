// plotws.js - MARCOS WebSocket Live Plotter (Darkmode & Interactive Controls)

(function () {
    const serveraddr = location.host ? location.host.split(':')[0] : 'localhost';
    const wsUrl = `ws://${serveraddr}:5000/`;
    const sensorblacklist = ['', 'none'];

    let wsconnection = null;
    let isPaused = false;
    let chartHeight = 180;
    let timeWindowSeconds = 180;

    // Speichert alle Signale: signals["SENSORID#0"] = { head, chart, timeSeries, card, checkbox, valueEl, visible }
    const signals = {};
    const sensorGroups = {};

    // DOM-Elemente
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
    const pauseBtn = document.getElementById('pauseBtn');
    const selectAllBtn = document.getElementById('selectAllBtn');
    const selectNoneBtn = document.getElementById('selectNoneBtn');
    const interpolationSelect = document.getElementById('interpolationSelect');

    serverInfoEl.textContent = `WebSocket: ${wsUrl}`;

    /**
     * Berechnet millisPerPixel basierend auf der aktuellen Canvas-Breite und dem gewählten Zeitfenster
     */
    function updateTimeScale() {
        timeWindowSeconds = Number(timeWindowSelect.value);
        const totalMs = timeWindowSeconds * 1000;

        // Sinnvolles Raster-Intervall für vertikale Zeitlinien wählen
        let millisPerLine = 10000;
        if (timeWindowSeconds <= 30) millisPerLine = 5000;
        else if (timeWindowSeconds <= 60) millisPerLine = 10000;
        else if (timeWindowSeconds <= 300) millisPerLine = 30000;
        else if (timeWindowSeconds <= 900) millisPerLine = 120000;
        else if (timeWindowSeconds <= 3600) millisPerLine = 600000;     // 10 Min.
        else if (timeWindowSeconds <= 43200) millisPerLine = 3600000;   // 1 Std.
        else millisPerLine = 7200000;                                   // 2 Std.

        Object.values(signals).forEach(sig => {
            const width = sig.canvas.clientWidth || sig.canvas.width || 800;
            sig.chart.options.millisPerPixel = totalMs / width;
            sig.chart.options.grid.millisPerLine = millisPerLine;
        });
    }

    /**
     * Passt die Canvas-Auflösung (Pixel) exakt an die dargestellte CSS-Größe an
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
     * Erzeugt einen neuen Eintrag in der Seitenleiste (Checkbox)
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
     * Schaltet die Sichtbarkeit eines Charts um
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
     * Erstellt Chart-Karte, Canvas, SmoothieChart und TimeSeries für ein Signal
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

        // SmoothieChart initialisieren
        const chart = new SmoothieChart(Object.assign({}, smoothiesettings, {
            maxDataSetLength: 86400
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

        // Direkt nach dem Einfügen ins DOM Größe & Zeitskala berechnen
        requestAnimationFrame(() => resizeCanvases());
    }

    /**
     * WebSocket-Verbindung aufbauen (inkl. automatischem Reconnect)
     */
    function connectWebSocket() {
        wsconnection = new WebSocket(wsUrl);

        wsconnection.onopen = function () {
            wsStatusBadge.classList.add('connected');
            wsStatusText.textContent = 'Connected';
            debugEl.textContent = 'WebSocket-connection activ.';
        };

        wsconnection.onmessage = function (e) {
            if (e.data[0] === '#') {
                // Header / Metadaten: # {"sensorid": ..., "nr": 0, "key": ..., "elem": ..., "unit": ...}
                try {
                    const jsonStr = e.data.substring(2);
                    const head = JSON.parse(jsonStr);
                    const signalid = `${head.sensorid}#${head.nr}`;

                    if (!signals[signalid] && !sensorblacklist.includes(head.sensorid)) {
                        createSignalChart(head, signalid);
                    }
                } catch (err) {
                    console.error('Error while parsing metadata:', err, e.data);
                }
            } else {
                // Messdaten: sensorid: timestamp,val0,val1...
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
                            // Daten immer puffern, damit beim Einblenden/Fortsetzen keine Lücken entstehen
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
                    debugEl.textContent = `Last package (${sensor}): ${dt.toLocaleTimeString()} | Values: ${dataArr.slice(1).join(', ')}`;
                }
            }
        };

        wsconnection.onclose = function () {
            wsStatusBadge.classList.remove('connected');
            wsStatusText.textContent = 'Disconnected (Reconnect...)';
            setTimeout(connectWebSocket, 3000);
        };

        wsconnection.onerror = function (error) {
            console.error('WebSocket error:', error);
            wsconnection.close();
        };
    }

    // --- Event-Listener für die UI-Steuerung ---

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
        pauseBtn.textContent = isPaused ? '▶ Continue' : '⏸ Pause';

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

    // Start
    connectWebSocket();
})();
