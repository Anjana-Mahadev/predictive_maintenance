// --- Debug Pipeline Integration ---
let lastSensorData = null;

// Save the latest streamed sensor data
function setLastSensorData(data) {
    lastSensorData = data;
}

// Call /debug_pipeline and show modal
async function debugPipelineWithLatestData() {
    if (!lastSensorData) {
        alert('No sensor data available yet. Start streaming first.');
        return;
    }
    const btn = document.getElementById('debug-btn');
    btn.disabled = true;
    btn.textContent = 'Debugging...';
    try {
        const resp = await fetch('/debug_pipeline', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(lastSensorData)
        });
        const result = await resp.json();
        showDebugModal(result.memory_snapshots);
    } catch (e) {
        alert('Debug pipeline failed: ' + e);
    }
    btn.disabled = false;
    btn.textContent = 'Debug Pipeline';
}

function showDebugModal(snapshots) {
    const modal = document.getElementById('debug-modal');
    const content = document.getElementById('debug-modal-content');
    if (!snapshots || !snapshots.length) {
        content.textContent = 'No debug data.';
    } else {
        content.innerHTML = snapshots.map((snap, idx) =>
            `<div style="margin-bottom:1.2em;"><b>Stage ${idx + 1}:</b><br><pre style="background:#181c20;padding:0.7em 1em;border-radius:6px;overflow-x:auto;">${JSON.stringify(snap, null, 2)}</pre></div>`
        ).join('');
    }
    modal.style.display = 'flex';
}

document.addEventListener('DOMContentLoaded', () => {
    // Modal close logic
    const modal = document.getElementById('debug-modal');
    const closeBtn = document.getElementById('close-debug-modal');
    if (closeBtn) closeBtn.onclick = () => { modal.style.display = 'none'; };
    // Debug button logic
    const debugBtn = document.getElementById('debug-btn');
    if (debugBtn) debugBtn.onclick = debugPipelineWithLatestData;
});

// Patch streaming to save last sensor data
const origEventSourceHandler = window.eventSource && window.eventSource.onmessage;
function patchEventSourceForDebug() {
    if (!window.eventSource) return;
    const orig = window.eventSource.onmessage;
    window.eventSource.onmessage = async function(event) {
        let data;
        try {
            data = JSON.parse(event.data.replace(/'/g, '"'));
        } catch (e) {
            try { data = eval('(' + event.data + ')'); } catch (e2) { return; }
        }
        setLastSensorData(data);
        if (orig) await orig.call(this, event);
    };
}
// Patch after streaming starts
const origStartStreaming = startStreaming;
startStreaming = function() {
    origStartStreaming();
    setTimeout(patchEventSourceForDebug, 100);
};
// Map sensor names to safe HTML IDs
function getSafeId(sensor) {
	return {
		'Air temperature [K]': 'sensor-graph-Air-temperature-K',
		'Process temperature [K]': 'sensor-graph-Process-temperature-K',
		'Rotational speed [rpm]': 'sensor-graph-Rotational-speed-rpm',
		'Torque [Nm]': 'sensor-graph-Torque-Nm',
		'Tool wear [min]': 'sensor-graph-Tool-wear-min',
	}[sensor];
}

// --- Mock Streaming Data ---
let streaming = false;
let intervalId = null;

// Example sensor names
const sensors = [
	'Air temperature [K]',
	'Process temperature [K]',
	'Rotational speed [rpm]',
	'Torque [Nm]',
	'Tool wear [min]'
];

// Generate random sensor data
function generateSensorData() {
        // Randomly pick a Type: 0 (H), 1 (M), 2 (L)
        const types = [0, 1, 2];
        const type = types[Math.floor(Math.random() * types.length)];
        return {
            'Air temperature [K]': 298 + Math.random() * 2,
            'Process temperature [K]': 308 + Math.random() * 2,
            'Rotational speed [rpm]': 1400 + Math.random() * 700,
            'Torque [Nm]': 20 + Math.random() * 30,
            'Tool wear [min]': Math.floor(Math.random() * 200),
            'Type': type
        };
}

// Generate data that will likely trigger a fault
function generateFaultySensorData() {
    // Use a fixed Type for faults (e.g., 1 for 'M')
    return {
        'Air temperature [K]': 310, // high
        'Process temperature [K]': 320, // high
        'Rotational speed [rpm]': 2100, // high
        'Torque [Nm]': 49, // high
        'Tool wear [min]': 199, // high
        'Type': 1
    };
}

// --- Plotly Live Graphs (one per variable) ---
let time = 0;
let graphData = {};

function initGraph() {
	time = 0;
	sensors.forEach(sensor => {
		graphData[sensor] = { x: [], y: [] };
		Plotly.newPlot(
			getSafeId(sensor),
			[{ x: [], y: [], name: sensor, mode: 'lines', line: { width: 2, color: '#1a73e8' } }],
			{
				margin: { t: 10, l: 30, r: 10, b: 20 },
				showlegend: false,
				xaxis: { title: '', showticklabels: false, showgrid: false, zeroline: false },
				yaxis: { title: '', showticklabels: false, showgrid: false, zeroline: false },
				paper_bgcolor: '#23272b',
				plot_bgcolor: '#23272b',
				height: 80
			},
			{ displayModeBar: false }
		);
	});
}

function updateGraph(sensorData) {
    time += 1;
    sensors.forEach(sensor => {
        if (!(sensor in sensorData)) {
            console.error('Missing sensor field in data:', sensor, sensorData);
            return;
        }
        graphData[sensor].x.push(time);
        graphData[sensor].y.push(sensorData[sensor]);
        Plotly.extendTraces(
            getSafeId(sensor),
            { x: [[time]], y: [[sensorData[sensor]]] },
            [0]
        );
        // Keep last 50 points
        if (graphData[sensor].x.length > 50) {
            graphData[sensor].x = graphData[sensor].x.slice(-50);
            graphData[sensor].y = graphData[sensor].y.slice(-50);
            Plotly.relayout(getSafeId(sensor), {
                'xaxis.range': [Math.max(0, time - 50), time]
            });
        }
    });
}


// --- Fault Type Mapping ---
const FAULT_TYPE_MAP = {
    0: 'None',
    1: 'TWF', // Tool Wear Failure
    2: 'HDF', // Heat Dissipation Failure
    3: 'PWF', // Power Failure
    4: 'OSF', // Overstrain Failure
    5: 'RNF', // Random Failure
    'TWF': 'TWF',
    'HDF': 'HDF',
    'PWF': 'PWF',
    'OSF': 'OSF',
    'RNF': 'RNF',
    'None': 'None',
    'none': 'None',
    '0': 'None',
    '': 'None',
    null: 'None',
    undefined: 'None'
};


let incidents = [];


function renderIncidents() {
    const container = document.getElementById('incidents-list');
    if (!container) return;
    container.innerHTML = '';
    // Show all incidents (not just faults)
    const getFaultTypeLabel = (fault) => {
        let val = fault;
        if (typeof val === 'string' && val.startsWith('Fault: ')) val = val.replace(/^Fault: /, '');
        if (typeof val === 'string' && !isNaN(Number(val))) val = Number(val);
        return FAULT_TYPE_MAP.hasOwnProperty(val) ? FAULT_TYPE_MAP[val] : val;
    };
    // Update incident count summary card (only real faults)
    const isFault = (incident) => {
        const faultVal = getFaultTypeLabel(incident.fault);
        return faultVal && faultVal !== 'None' && faultVal !== 'No Fault' && faultVal !== '0';
    };
    const faultIncidents = incidents.filter(isFault);
    const countCard = document.getElementById('incident-count');
    if (countCard) countCard.textContent = faultIncidents.length;
    if (incidents.length === 0) {
        container.innerHTML = '<div class="incident-list-empty">No incidents yet. All systems normal.</div>';
        return;
    }
    incidents.slice().reverse().forEach((incident, idx) => {
        const card = document.createElement('div');
        card.className = 'incident-card';
        const faultType = getFaultTypeLabel(incident.fault);
        card.innerHTML = `
            <div class="incident-card-header">
                <span class="incident-fault-type ${faultType !== 'None' ? 'faulty' : 'healthy'}">${faultType || 'None'}</span>
                <span class="incident-confidence">Confidence: <b>${typeof incident.confidence === 'number' ? (incident.confidence * 100).toFixed(1) + '%' : 'N/A'}</b></span>
                <span class="incident-time">${incident.time || incident.timestamp || ''}</span>
            </div>
            <div class="incident-card-body">
                <div><strong>Root Cause:</strong> <span>${incident.root_cause || incident.rootCause || 'N/A'}</span></div>
                <div><strong>Recommendations:</strong><ul>${(incident.recommendations || []).map(r => {
                    if (typeof r === 'object' && r !== null) {
                        const rec = r.Recommendation || r.recommendation || '';
                        const desc = r.Description || r.description || '';
                        return `<li><b>${rec}</b><br><span style='font-size:90%'>${desc}</span></li>`;
                    } else {
                        return `<li>${r}</li>`;
                    }
                }).join('')}</ul></div>
            </div>
        `;
        card.onclick = () => {
            window.location.href = '/incident.html?id=' + encodeURIComponent(getIncidentId(incident));
        };
        container.appendChild(card);
    });
    // Save all incidents to localStorage for details page access
    try { localStorage.setItem('incidents', JSON.stringify(incidents)); } catch {}
}

// --- Add incident from backend ---
function setIncidentDetailsFromBackend(incident) {
    if (incident && typeof incident.fault !== 'undefined') {
        let faultLabel;
        const noFaultValues = [undefined, null, '', 0, '0', 'None', 'none', false];
        if (noFaultValues.includes(incident.fault)) {
            faultLabel = 'None';
        } else if (typeof incident.fault === 'string' && incident.fault.trim().toLowerCase() === 'none') {
            faultLabel = 'None';
        } else {
            faultLabel = incident.fault.toString().replace(/^Fault: /, '').trim();
        }
        const newIncident = {
            ...incident,
            fault: faultLabel,
            root_cause: incident.root_cause || incident.rootCause || 'N/A',
            recommendations: incident.recommendations && incident.recommendations.length ? incident.recommendations : ['N/A'],
            time: new Date().toLocaleString(),
            incident_id: incident.incident_id || Date.now().toString()
        };
        incidents.push(newIncident);
        try { localStorage.setItem('incidents', JSON.stringify(incidents)); } catch {}
    }
    renderIncidents();
}

// --- Utility: Unique incident ID ---
function getIncidentId(incident) {
    return incident.incident_id || incident.timestamp || incident.time || '';
}

// --- On load, render incidents and initialize graph ---
document.addEventListener('DOMContentLoaded', function() {
    renderIncidents();
    initGraph();
    setSystemHealth(true);
});

// Replace clearAllData
function clearAllData() {
    time = 0;
    sensors.forEach(sensor => {
        graphData[sensor] = { x: [], y: [] };
        Plotly.newPlot(
            getSafeId(sensor),
            [{ x: [], y: [], name: sensor, mode: 'lines' }],
            {
                margin: { t: 30 },
                showlegend: false,
                xaxis: { title: 'Time (s)' },
                yaxis: { title: sensor }
            }
        );
    });
    incidents = [];
    renderIncidents();
    setSystemHealth(true);
}

// --- Streaming Logic ---
function startStreaming() {
    if (streaming) return;
    streaming = true;
    document.getElementById('start-btn').disabled = true;
    document.getElementById('stop-btn').disabled = false;
    incidents = [];
    renderIncidents();
    setSystemHealth(true);
    // Use EventSource to connect to backend /stream endpoint
    window.eventSource = new EventSource('/stream');
    window.eventSource.onmessage = async function(event) {
        if (!streaming) return;
        let data;
        try {
            data = JSON.parse(event.data.replace(/'/g, '"'));
        } catch (e) {
            // fallback: try eval (for python dict string)
            try { data = eval('(' + event.data + ')'); } catch (e2) { return; }
        }
        console.log('Received streaming data:', data);
        updateGraph(data);
        showIncidentLoading();
        const result = await callAgenticPipeline(data);
        const noFaultValues = [undefined, null, '', 0, '0', 'None', 'none', false];
        let isNoFault = false;
        if (noFaultValues.includes(result.fault) || (typeof result.fault === 'string' && result.fault.trim().toLowerCase() === 'none')) {
            isNoFault = true;
        }
        if (!isNoFault) {
            setSystemHealth(false);
            setIncidentDetailsFromBackend(result);
        } else {
            setSystemHealth(true);
            setIncidentDetailsFromBackend(result);
        }
    };
    window.eventSource.onerror = function() {
        setSystemHealth(false);
    };
}

function stopStreaming() {
    if (!streaming) return;
    streaming = false;
    document.getElementById('start-btn').disabled = false;
    document.getElementById('stop-btn').disabled = true;
    if (window.eventSource) {
        window.eventSource.close();
        window.eventSource = null;
    }
}

document.getElementById('start-btn').addEventListener('click', startStreaming);
document.getElementById('stop-btn').addEventListener('click', stopStreaming);
document.getElementById('clear-btn').addEventListener('click', clearAllData);

document.addEventListener('DOMContentLoaded', function() {
    renderIncidents();
    initGraph();
    setSystemHealth(true);
});

// --- Modern Fault Incident List (Gmail-style, only real faults) ---
// function renderIncidentList() {
//     const list = document.getElementById('incidents-list');
//     const empty = document.getElementById('incident-list-empty');
//     if (!list) return;
//     let incidents = [];
//     try {
//         incidents = JSON.parse(localStorage.getItem('incidents') || '[]');
//     } catch { incidents = []; }
//     // Only show real faults (robust to label prefix)
//     const realFaults = incidents.filter(inc => {
//         let val = (inc.fault || inc.Fault || '').toString().replace(/^Fault: /, '').trim();
//         return val && val !== 'None' && val !== '0' && val !== 'No Fault';
//     });
//     list.innerHTML = '';
//     if (!realFaults.length) {
//         if (empty) empty.style.display = '';
//         return;
//     }
//     if (empty) empty.style.display = 'none';
//     realFaults.slice().reverse().forEach((incident, idx) => {
//         const row = document.createElement('div');
//         row.className = 'incident-row' + (incident.unread ? ' unread' : '');
//         let ft = (incident.fault || incident.Fault || 'N').toString().replace(/^Fault: /, '').trim();
//         const avatar = document.createElement('div');
//         avatar.className = 'incident-avatar';
//         avatar.textContent = ft[0] ? ft[0].toUpperCase() : '!';
//         row.appendChild(avatar);
//         const main = document.createElement('div');
//         main.className = 'incident-main';
//         const title = document.createElement('div');
//         title.className = 'incident-title';
//         // Show root cause or a clear message
//         if (ft !== 'None') {
//             title.textContent = incident.root_cause || incident.rootCause || `Fault detected: ${ft}`;
//         } else {
//             title.textContent = 'System is normal';
//         }
//         main.appendChild(title);
//         const meta = document.createElement('div');
//         meta.className = 'incident-meta';
//         const badge = document.createElement('span');
//         badge.className = 'incident-badge ' + (ft !== 'None' ? 'faulty' : 'healthy');
//         badge.textContent = ft;
//         meta.appendChild(badge);
//         const time = document.createElement('span');
//         time.className = 'incident-time';
//         time.textContent = incident.timestamp ? new Date(incident.timestamp).toLocaleString() : (incident.time || '');
//         meta.appendChild(time);
//         main.appendChild(meta);
//         // Show recommendations if fault, else nothing
//         if (ft !== 'None' && incident.recommendations && incident.recommendations.length) {
//             const recs = document.createElement('div');
//             recs.innerHTML = `<strong>Recommendations:</strong><ul>${incident.recommendations.map(r => {
//                 if (typeof r === 'object' && r !== null) {
//                     const rec = r.Recommendation || r.recommendation || '';
//                     const desc = r.Description || r.description || '';
//                     return `<li><b>${rec}</b><br><span style='font-size:90%'>${desc}</span></li>`;
//                 } else {
//                     return `<li>${r}</li>`;
//                 }
//             }).join('')}</ul>`;
//             main.appendChild(recs);
//         }
//         row.appendChild(main);
//         row.onclick = () => {
//             incident.unread = false;
//             localStorage.setItem('incidents', JSON.stringify(incidents));
//             window.location.href = '/incident.html?idx=' + (incidents.length - 1 - idx);
//         };
//         list.appendChild(row);
//     });
// }

// --- Simplified Graph Rendering for Mini Graphs with Labels ---
function initGraph() {
    time = 0;
    sensors.forEach(sensor => {
        graphData[sensor] = { x: [], y: [] };
        Plotly.newPlot(
            getSafeId(sensor),
            [{ x: [], y: [], name: sensor, mode: 'lines', line: { width: 2, color: '#1a73e8' } }],
            {
                margin: { t: 10, l: 30, r: 10, b: 30 },
                showlegend: false,
                xaxis: { title: 'Time (s)', showticklabels: false, showgrid: false, zeroline: false, titlefont: { color: '#a0aec0', size: 10 } },
                yaxis: { title: sensor, showticklabels: false, showgrid: false, zeroline: false, titlefont: { color: '#a0aec0', size: 10 } },
                paper_bgcolor: '#23272b',
                plot_bgcolor: '#23272b',
                height: 80
            },
            { displayModeBar: false }
        );
    });
}

// --- On load ---
document.addEventListener('DOMContentLoaded', function() {
    renderIncidents();
    initGraph();
    setSystemHealth(true);
});
