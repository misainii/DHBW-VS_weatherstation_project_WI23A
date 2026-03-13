const translations = {
  de: {
    // General
    appTitle: "Weatherstation Explorer",
    browserPath: "wetterstation.draft/3.1.1",
    // Search page
    searchTitle: 'Suche nach <span class="circled">mehr</span>…',
    searchSidebarTitle: "Suche nach deiner Station",
    latitudeLabel: "Breitengrad:",
    longitudeLabel: "Längengrad:",
    radiusLabel: "Radius (km):",
    limitLabel: "Auswahl:",
    startYearLabel: "Start:",
    endYearLabel: "Ende:",
    searchButton: "Suchen!",
    searchFeedbackNotFound: "Station konnte nicht gefunden werden. Versuche es erneut.",
    heroText: "Finde Wetterstationen, die zum Global Historical Climatology Network beitragen",
    // Stations page
    stationsTitle: '<span class="circled">Verfügbare</span> Stationen …',
    stationsSidebarTitle: "Suche nach deiner Station",
    selectByNameLabel: "Nach Name auswählen:",
    showDataButton: "Daten anzeigen",
    backButton: "Zurück",
    stationNotes1: "Klicke auf die Marker auf der Karte, um eine Station auszuwählen",
    stationNotes2: "Einige Stationen enthalten fehlende Daten!",
    stationTableName: "Name",
    stationTableDistance: "Entfernung",
    stationTableData: "Daten",
    stationTableChoose: "Auswählen",
    // Climate page
    climateSidebarTitle: "Daten für deine Station",
    climateTitle: 'Daten für <span id="climateTitleStation">Station</span> …',
    legendTitle: "Datenreihen",
    gapWarning: "Warnung: Datenlücken vorhanden",
    compactTableYear: "Jahr",
    selectNewStationButton: "Neue Station auswählen",
    backToStationsButton: "Zurück zu den Stationen",
    // Error messages (general)
    errorPrefix: "Fehler:",
    noDataSelected: "Keine Daten ausgewählt",
    noPoints: "Keine Punkte vorhanden",
    noTableData: "Keine Tabellendaten verfügbar.",
    noDataForSelected: "Keine Daten für ausgewählte Reihen.",
  },
  en: {
    // General
    appTitle: "Weatherstation Explorer",
    browserPath: "weatherstation.draft/3.1.1",
    // Search page
    searchTitle: 'Search for <span class="circled">more</span>…',
    searchSidebarTitle: "Search for your station",
    latitudeLabel: "Latitude:",
    longitudeLabel: "Longitude:",
    radiusLabel: "Radius (km):",
    limitLabel: "Selection:",
    startYearLabel: "Start:",
    endYearLabel: "End:",
    searchButton: "Search!",
    searchFeedbackNotFound: "Station couldn't be found. Try again.",
    heroText: "Find weather stations contributing to the Global Historical Climatology Network",
    // Stations page
    stationsTitle: '<span class="circled">Available</span> Stations …',
    stationsSidebarTitle: "Search for your station",
    selectByNameLabel: "Select by Name:",
    showDataButton: "Show Data",
    backButton: "Back",
    stationNotes1: "Click on map markers to select a station",
    stationNotes2: "Some stations contain missing data!",
    stationTableName: "Name",
    stationTableDistance: "Distance",
    stationTableData: "Data",
    stationTableChoose: "Choose",
    // Climate page
    climateSidebarTitle: "Data for your station",
    climateTitle: '<span id="climateTitleStation">Station</span> data…',
    legendTitle: "Data series",
    gapWarning: "Warning: Data gaps present",
    compactTableYear: "Year",
    selectNewStationButton: "Select New Station",
    backToStationsButton: "Back to Stations",
    // Error messages
    errorPrefix: "Error:",
    noDataSelected: "No data selected",
    noPoints: "No points available",
    noTableData: "No table data available.",
    noDataForSelected: "No data for selected series.",
  }
};

const state = {
    stations: [],
    selectedId: null,
    climate: null,
    page: 'search',
    activeSeries: new Set(['annual_tmin', 'annual_tmax', 'spring_tmin', 'spring_tmax', 'summer_tmin', 'summer_tmax', 'autumn_tmin', 'autumn_tmax', 'winter_tmin', 'winter_tmax']),
    map: null,
    markers: [],
    radiusCircle: null,  // search radius circle
    language: 'de'       // default, will be overridden later
};

const $ = id => document.getElementById(id);

function showPage(page) {
    state.page = page;
    $('pageSearch').classList.toggle('hidden', page !== 'search');
    $('pageStations').classList.toggle('hidden', page !== 'stations');
    $('pageClimate').classList.toggle('hidden', page !== 'climate');
    if (page === 'stations') setTimeout(initMap, 100);
}

// Translation functions
function setLanguage(lang) {
    if (lang === state.language) return;
    state.language = lang;
    translatePage();
    // Redraw dynamic parts not covered by translatePage
    if (state.page === 'stations') {
        renderStationTable(); // table header is already translated, but select options?
        // Select options contain station names, they remain unchanged.
    } else if (state.page === 'climate') {
        renderClimate();
    }
    localStorage.setItem('preferred-language', lang);
}

function translatePage() {
    const lang = state.language;
    const t = translations[lang];

    // All elements with data-i18n (plain text)
    document.querySelectorAll('[data-i18n]').forEach(el => {
        const key = el.getAttribute('data-i18n');
        if (t[key] !== undefined) {
            el.innerText = t[key];
        }
    });

    // All elements with data-i18n-html (HTML content)
    document.querySelectorAll('[data-i18n-html]').forEach(el => {
        const key = el.getAttribute('data-i18n-html');
        if (t[key] !== undefined) {
            el.innerHTML = t[key];
        }
    });

    // All elements with data-i18n-placeholder (placeholder attribute)
    document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
        const key = el.getAttribute('data-i18n-placeholder');
        if (t[key] !== undefined) {
            el.placeholder = t[key];
        }
    });

    // Browser path
    const browserPathEl = $('browserPath');
    if (browserPathEl) {
        browserPathEl.innerText = t.browserPath;
    }
}

async function searchStations() {
    const feedback = $('searchFeedback');
    // Clear previous message
    feedback.textContent = '';
    feedback.classList.remove('error');

    const params = new URLSearchParams({
        latitude: $('latitude').value,
        longitude: $('longitude').value,
        radius_km: $('radius').value,
        limit: $('limit').value,
        start_year: $('startYear').value,
        end_year: $('endYear').value
    });
    try {
        const res = await fetch(`/api/stations?${params}`);
        if (!res.ok) {
            const text = await res.text();
            throw new Error(`Server responds with ${res.status}: ${text}`);
        }
        const data = await res.json();
        // Check if stations were found
        if (!data.stations || data.stations.length === 0) {
            feedback.textContent = translations[state.language].searchFeedbackNotFound;
            feedback.classList.add('error');
            return; // Do not switch to stations page
        }
        state.stations = data.stations;
        state.selectedId = state.stations[0]?.station_id || null;
        renderStationTable();
        showPage('stations');
    } catch (err) {
        alert(translations[state.language].errorPrefix + ' ' + err.message);
    }
}

function renderStationTable() {
    const tbody = $('stationTable').querySelector('tbody');
    tbody.innerHTML = '';
    state.stations.forEach(s => {
        const row = tbody.insertRow();
        row.innerHTML = `
            <td>${s.name}</td>
            <td>${s.distance_km?.toFixed(1) || '?'} km</td>
            <td>${s.first_year || '?'} - ${s.last_year || '?'}</td>
            <td><button onclick="window.selectStation('${s.station_id}')">${translations[state.language].stationTableChoose}</button></td>
        `;
    });
    const select = $('stationSelect');
    select.innerHTML = '';
    state.stations.forEach(s => {
        const opt = document.createElement('option');
        opt.value = s.station_id;
        opt.text = s.name;
        opt.selected = s.station_id === state.selectedId;
        select.appendChild(opt);
    });
}

window.selectStation = (id) => {
    state.selectedId = id;
    loadClimate();
};

async function loadClimate() {
    try {
        const res = await fetch(`/api/stations/${state.selectedId}/climate?start_year=${$('startYear').value}&end_year=${$('endYear').value}`);
        if (!res.ok) {
            const text = await res.text();
            throw new Error(`Server responds with ${res.status}: ${text}`);
        }
        const data = await res.json();
        state.climate = data;
        // Debug output in console
        console.log('Climate data received:', data);
        console.log('Seasonal series:', data.seasonal_series);
        renderClimate();
        showPage('climate');
    } catch (err) {
        alert(translations[state.language].errorPrefix + ' ' + err.message);
    }
}

function renderClimate() {
    $('climateTitleStation').textContent = state.climate.station.name;
    renderLegend();
    renderTable();
    drawChart();
}

function renderLegend() {
    const legend = $('chartLegend');
    legend.innerHTML = '';

    // All existing series (annual + seasonal)
    const allSeries = [
        ...(state.climate?.annual_series || []),
        ...(state.climate?.seasonal_series || [])
    ];

    console.log('All series for legend:', allSeries);

    if (allSeries.length === 0) {
        legend.innerHTML = '<p>No data series available.</p>';
        return;
    }

    // Color mapping
    const colorMap = {
        'annual_tmin': '#2d73c4',
        'annual_tmax': '#d23d30',
        'spring_tmin': '#5ba357',
        'spring_tmax': '#8dc46e',
        'summer_tmin': '#e4ab51',
        'summer_tmax': '#d18a2c',
        'autumn_tmin': '#c2bfba',
        'autumn_tmax': '#8d8a87',
        'winter_tmin': '#7ba2d6',
        'winter_tmax': '#9a9ac6'
    };

    allSeries.forEach(s => {
        const name = s.name;
        const label = state.language === 'de' ? s.label_de : s.label_en || name;
        const color = colorMap[name] || '#888';

        const labelEl = document.createElement('label');
        const cb = document.createElement('input');
        cb.type = 'checkbox';
        cb.checked = state.activeSeries.has(name);
        cb.onchange = () => toggleSeries(name);

        const swatch = document.createElement('span');
        swatch.style.cssText = `display:inline-block; width:20px; height:3px; background:${color}; margin:0 5px;`;

        labelEl.appendChild(cb);
        labelEl.appendChild(swatch);
        labelEl.appendChild(document.createTextNode(label));
        legend.appendChild(labelEl);
    });
}

function toggleSeries(name) {
    if (state.activeSeries.has(name)) state.activeSeries.delete(name);
    else state.activeSeries.add(name);
    renderTable();
    drawChart();
}

function renderTable() {
    const container = $('compactTable');
    if (!state.climate?.table) {
        container.innerHTML = `<p>${translations[state.language].noTableData}</p>`;
        return;
    }

    // All available series (annual + seasonal)
    const allSeries = [
        ...(state.climate.annual_series || []),
        ...(state.climate.seasonal_series || [])
    ];
    const seriesMap = {};
    allSeries.forEach(s => seriesMap[s.name] = s);

    const active = Array.from(state.activeSeries).filter(name => 
        state.climate.table.some(row => row[name] !== undefined)
    );

    if (active.length === 0) {
        container.innerHTML = `<p>${translations[state.language].noDataForSelected}</p>`;
        return;
    }

    let html = '<table><thead><tr><th>' + translations[state.language].compactTableYear + '</th>';
    active.forEach(name => {
        const s = seriesMap[name];
        const label = s ? (state.language === 'de' ? s.label_de : s.label_en) : name;
        html += `<th>${label}</th>`;
    });
    html += '</tr></thead><tbody>';

    state.climate.table.forEach(row => {
        html += `<tr><td>${row.year}</td>`;
        active.forEach(name => {
            const val = row[name];
            html += `<td>${val !== undefined ? val.toFixed(1) : '–'}</td>`;
        });
        html += '</tr>';
    });

    html += '</tbody></table>';
    container.innerHTML = html;
}

function drawChart() {
    const svg = $('chart');
    svg.innerHTML = '';
    if (!state.climate) return;

    const allSeries = [
        ...(state.climate.annual_series || []),
        ...(state.climate.seasonal_series || [])
    ];
    const activeSeriesData = allSeries.filter(s => state.activeSeries.has(s.name));

    if (activeSeriesData.length === 0) {
        svg.innerHTML = `<text x="380" y="200" text-anchor="middle">${translations[state.language].noDataSelected}</text>`;
        return;
    }

    const points = activeSeriesData.flatMap(s => s.points);
    if (points.length === 0) {
        svg.innerHTML = `<text x="380" y="200" text-anchor="middle">${translations[state.language].noPoints}</text>`;
        return;
    }

    const years = points.map(p => p.year);
    const values = points.map(p => p.value);
    const minYear = Math.min(...years);
    const maxYear = Math.max(...years);
    const minVal = Math.floor(Math.min(...values));
    const maxVal = Math.ceil(Math.max(...values));

    const w = 760, h = 400;
    const pad = {l: 70, r: 30, t: 30, b: 50};

    svg.innerHTML += `<rect x="0" y="0" width="${w}" height="${h}" fill="white"/>`;

    // Y axis
    for (let i = 0; i <= 5; i++) {
        const val = minVal + (maxVal - minVal) * i / 5;
        const y = pad.t + (h - pad.t - pad.b) * (1 - (val - minVal) / (maxVal - minVal));
        svg.innerHTML += `<line x1="${pad.l}" y1="${y}" x2="${w-pad.r}" y2="${y}" stroke="#eee" stroke-dasharray="4"/>`;
        svg.innerHTML += `<text x="${pad.l-10}" y="${y+5}" text-anchor="end">${val.toFixed(1)}</text>`;
    }

    // X axis
    for (let y = minYear; y <= maxYear; y += Math.ceil((maxYear-minYear)/8)) {
        const x = pad.l + (w - pad.l - pad.r) * (y - minYear) / (maxYear - minYear);
        svg.innerHTML += `<line x1="${x}" y1="${pad.t}" x2="${x}" y2="${h-pad.b}" stroke="#eee" stroke-dasharray="4"/>`;
        svg.innerHTML += `<text x="${x}" y="${h-20}" text-anchor="middle">${y}</text>`;
    }

    const colorMap = {
        'annual_tmin': '#2d73c4',
        'annual_tmax': '#d23d30',
        'spring_tmin': '#5ba357',
        'spring_tmax': '#8dc46e',
        'summer_tmin': '#e4ab51',
        'summer_tmax': '#d18a2c',
        'autumn_tmin': '#c2bfba',
        'autumn_tmax': '#8d8a87',
        'winter_tmin': '#7ba2d6',
        'winter_tmax': '#9a9ac6'
    };

    activeSeriesData.forEach(s => {
        const color = colorMap[s.name] || '#888';
        const sorted = [...s.points].sort((a,b) => a.year - b.year);

        // lines only between directly following years
        let start = 0;
        for (let i = 1; i <= sorted.length; i++) {
            if (i === sorted.length || sorted[i].year - sorted[i-1].year > 1) {
                if (i - start >= 2) {
                    const segment = sorted.slice(start, i);
                    const pts = segment.map(p => {
                        const x = pad.l + (w - pad.l - pad.r) * (p.year - minYear) / (maxYear - minYear);
                        const y = pad.t + (h - pad.t - pad.b) * (1 - (p.value - minVal) / (maxVal - minVal));
                        return `${x},${y}`;
                    }).join(' ');
                    svg.innerHTML += `<polyline points="${pts}" fill="none" stroke="${color}" stroke-width="2"/>`;
                }
                start = i;
            }
        }

        // dots
        sorted.forEach(p => {
            const x = pad.l + (w - pad.l - pad.r) * (p.year - minYear) / (maxYear - minYear);
            const y = pad.t + (h - pad.t - pad.b) * (1 - (p.value - minVal) / (maxVal - minVal));
            svg.innerHTML += `<circle cx="${x}" cy="${y}" r="3" fill="${color}"/>`;
        });
    });

    svg.innerHTML += `<text x="20" y="200" transform="rotate(-90 20 200)">°C</text>`;
    svg.innerHTML += `<text x="${w/2}" y="${h-5}" text-anchor="middle">Year</text>`;
}

function initMap() {
    const lat = Number($('latitude').value);
    const lon = Number($('longitude').value);
    const radiusKm = Number($('radius').value) || 60; // Fallback if empty

    if (!state.map) {
        state.map = L.map('leafletMap').setView([lat, lon], 7);
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(state.map);
    } else {
        state.map.setView([lat, lon], 7);
    }

    // remove old markers
    if (state.markers) {
        state.markers.forEach(m => m.remove());
    }
    state.markers = [];

    // remove old radius
    if (state.radiusCircle) {
        state.radiusCircle.remove();
    }

    // search center
    L.circleMarker([lat, lon], {
        radius: 8,
        color: '#dc3545',
        fillColor: '#dc3545',
        fillOpacity: 1
    }).addTo(state.map).bindTooltip('Search Center');

    // draw radius circle
    state.radiusCircle = L.circle([lat, lon], {
        radius: radiusKm * 1000,
        color: '#dc3545',
        fillColor: '#dc3545',
        fillOpacity: 0.1,
        weight: 2,
        interactive: false  // prevents the circle from intercepting clicks
    }).addTo(state.map);

    // stations as markers
    state.stations.forEach(s => {
        const m = L.circleMarker([s.latitude, s.longitude], {
            radius: s.station_id === state.selectedId ? 8 : 6,
            color: s.station_id === state.selectedId ? '#ffc107' : '#28a745',
            fillColor: s.station_id === state.selectedId ? '#ffc107' : '#28a745',
            fillOpacity: 1
        }).addTo(state.map);
        m.bindTooltip(`${s.name} (${s.distance_km?.toFixed(1)} km)`);
        m.on('click', () => {
            state.selectedId = s.station_id;
            initMap(); // redraw map (markers will be updated)
            renderStationTable();
        });
        state.markers.push(m);
    });

    // zoom to show all stations + center
    if (state.stations.length > 0) {
        const bounds = L.latLngBounds([[lat, lon]]);
        state.stations.forEach(s => bounds.extend([s.latitude, s.longitude]));
        state.map.fitBounds(bounds, { padding: [50, 50] });
    } else {
        // If no stations, zoom to center anyway (radius visible)
        state.map.setView([lat, lon], 8);
    }
}

// Initialization
const savedLang = localStorage.getItem('preferred-language');
const browserLang = navigator.language.startsWith('de') ? 'de' : 'en';
state.language = savedLang || browserLang;

document.querySelectorAll('.lang-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
        setLanguage(e.target.dataset.lang);
    });
});

$('searchForm').addEventListener('submit', (e) => { e.preventDefault(); searchStations(); });
$('showDataButton').addEventListener('click', () => { if (state.selectedId) loadClimate(); });
$('backToSearchButton').addEventListener('click', () => showPage('search'));
$('selectNewStationButton').addEventListener('click', () => showPage('search'));
$('backToStationsButton').addEventListener('click', () => showPage('stations'));
$('stationSelect').addEventListener('change', (e) => {
    state.selectedId = e.target.value;
    renderStationTable();
    initMap();
});

showPage('search');
translatePage(); // Initial translation
