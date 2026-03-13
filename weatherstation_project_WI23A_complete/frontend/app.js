const state = {
    stations: [],
    selectedId: null,
    climate: null,
    page: 'search',
    activeSeries: new Set(['annual_tmin', 'annual_tmax', 'spring_tmin', 'spring_tmax', 'summer_tmin', 'summer_tmax', 'autumn_tmin', 'autumn_tmax', 'winter_tmin', 'winter_tmax']),
    map: null,
    markers: [],
    radiusCircle: null  // für den Kreis des Suchradius
};

const $ = id => document.getElementById(id);

function showPage(page) {
    state.page = page;
    $('pageSearch').classList.toggle('hidden', page !== 'search');
    $('pageStations').classList.toggle('hidden', page !== 'stations');
    $('pageClimate').classList.toggle('hidden', page !== 'climate');
    if (page === 'stations') setTimeout(initMap, 100);
}

async function searchStations() {
    const feedback = $('searchFeedback');
    // Vorherige Meldung löschen
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
            throw new Error(`Server antwortet mit ${res.status}: ${text}`);
        }
        const data = await res.json();
        // Prüfen, ob Stationen gefunden wurden
        if (!data.stations || data.stations.length === 0) {
            feedback.textContent = "Station couldn't be found. Try again.";
            feedback.classList.add('error');
            return; // Nicht zur Stationsseite wechseln
        }
        state.stations = data.stations;
        state.selectedId = state.stations[0]?.station_id || null;
        renderStationTable();
        showPage('stations');
    } catch (err) {
        alert('Fehler: ' + err.message);
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
            <td><button onclick="window.selectStation('${s.station_id}')">Select</button></td>
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
            throw new Error(`Server antwortet mit ${res.status}: ${text}`);
        }
        const data = await res.json();
        state.climate = data;
        // Debug-Ausgaben in der Konsole
        console.log('Climate data received:', data);
        console.log('Seasonal series:', data.seasonal_series);
        renderClimate();
        showPage('climate');
    } catch (err) {
        alert('Fehler: ' + err.message);
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

    // Alle vorhandenen Reihen (annual + seasonal)
    const allSeries = [
        ...(state.climate?.annual_series || []),
        ...(state.climate?.seasonal_series || [])
    ];

    console.log('All series for legend:', allSeries);

    if (allSeries.length === 0) {
        legend.innerHTML = '<p>Keine Datenreihen verfügbar.</p>';
        return;
    }

    // Farbzuordnung
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
        const label = s.label_de || s.label_en || name;
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
        container.innerHTML = '<p>Keine Tabellendaten verfügbar.</p>';
        return;
    }

    // Nur Spalten für aktive Reihen, die auch in der Tabelle vorkommen
    const active = Array.from(state.activeSeries).filter(name => 
        state.climate.table.some(row => row[name] !== undefined)
    );

    if (active.length === 0) {
        container.innerHTML = '<p>Keine Daten für ausgewählte Reihen.</p>';
        return;
    }

    let html = '<table><thead><tr><th>Year</th>';
    active.forEach(name => html += `<th>${name.replace('_', ' ').toUpperCase()}</th>`);
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
        svg.innerHTML = '<text x="380" y="200" text-anchor="middle">Keine Daten ausgewählt</text>';
        return;
    }

    const points = activeSeriesData.flatMap(s => s.points);
    if (points.length === 0) {
        svg.innerHTML = '<text x="380" y="200" text-anchor="middle">Keine Punkte vorhanden</text>';
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

    // Y-Achse
    for (let i = 0; i <= 5; i++) {
        const val = minVal + (maxVal - minVal) * i / 5;
        const y = pad.t + (h - pad.t - pad.b) * (1 - (val - minVal) / (maxVal - minVal));
        svg.innerHTML += `<line x1="${pad.l}" y1="${y}" x2="${w-pad.r}" y2="${y}" stroke="#eee" stroke-dasharray="4"/>`;
        svg.innerHTML += `<text x="${pad.l-10}" y="${y+5}" text-anchor="end">${val.toFixed(1)}</text>`;
    }

    // X-Achse
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

        // Linien nur zwischen aufeinanderfolgenden Jahren
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

        // Punkte zeichnen
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
    const radiusKm = Number($('radius').value) || 60; // Fallback, falls leer

    if (!state.map) {
        state.map = L.map('leafletMap').setView([lat, lon], 7);
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(state.map);
    } else {
        state.map.setView([lat, lon], 7);
    }

    // Alte Marker entfernen
    if (state.markers) {
        state.markers.forEach(m => m.remove());
    }
    state.markers = [];

    // Alten Kreis entfernen, falls vorhanden
    if (state.radiusCircle) {
        state.radiusCircle.remove();
    }

    // Suchzentrum als Marker
    L.circleMarker([lat, lon], {
        radius: 8,
        color: '#dc3545',
        fillColor: '#dc3545',
        fillOpacity: 1
    }).addTo(state.map).bindTooltip('Search Center');

    // Radius-Kreis zeichnen
    state.radiusCircle = L.circle([lat, lon], {
        radius: radiusKm * 1000,
        color: '#dc3545',
        fillColor: '#dc3545',
        fillOpacity: 0.1,
        weight: 2,
        interactive: false  // verhindert, dass der Kreis Klicks abfängt
    }).addTo(state.map);

    // Stationen als Marker
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
            initMap(); // Karte neu zeichnen (Marker werden aktualisiert)
            renderStationTable();
        });
        state.markers.push(m);
    });

    // Zoom anpassen, um alle Stationen + Zentrum zu zeigen
    if (state.stations.length > 0) {
        const bounds = L.latLngBounds([[lat, lon]]);
        state.stations.forEach(s => bounds.extend([s.latitude, s.longitude]));
        state.map.fitBounds(bounds, { padding: [50, 50] });
    } else {
        // Wenn keine Stationen, trotzdem auf Zentrum zoomen (Radius sichtbar)
        state.map.setView([lat, lon], 8);
    }
}

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
