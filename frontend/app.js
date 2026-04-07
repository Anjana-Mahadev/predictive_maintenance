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
			[{ x: [], y: [], name: sensor, mode: 'lines' }],
			{
				margin: { t: 30 },
				showlegend: false,
				xaxis: { title: 'Time (s)' },
				yaxis: { title: sensor }
			}
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

// --- Incident Storage ---
let incidents = [];

function renderIncidents() {
    const container = document.getElementById('incidents-list');
    if (!container) return;
    container.innerHTML = '';
    if (incidents.length === 0) {
        const empty = document.createElement('div');
        empty.className = 'incident-empty';
        empty.textContent = 'No incidents recorded.';
        container.appendChild(empty);
        return;
    }
    // Tabbed UI for incidents
    const tabs = document.createElement('div');
    tabs.className = 'incident-tabs';
    const tabContent = document.createElement('div');
    tabContent.className = 'incident-tab-content';
    let activeIdx = 0;
    // If a tab was previously selected, keep it
    if (window.activeIncidentTab !== undefined && window.activeIncidentTab < incidents.length) {
        activeIdx = window.activeIncidentTab;
    }
    incidents.forEach((incident, idx) => {
        const tab = document.createElement('button');
        tab.className = 'incident-tab' + (idx === activeIdx ? ' active' : '');
        tab.textContent = `Incident ${idx + 1}`;
        tab.onclick = () => {
            window.activeIncidentTab = idx;
            renderIncidents();
        };
        tabs.appendChild(tab);
    });
    // Render active incident details
    const incident = incidents[activeIdx];
    const div = document.createElement('div');
    div.className = 'incident-entry';
    div.innerHTML = `<div><strong>Fault:</strong> ${incident.fault}</div>` +
        `<div><strong>Root Cause:</strong> ${incident.rootCause}</div>` +
        `<div><strong>Recommendations:</strong><ul>${incident.recommendations.map(r => {
            if (typeof r === 'object' && r !== null) {
                // Render Recommendation and Description fields if present
                const rec = r.Recommendation || r.recommendation || '';
                const desc = r.Description || r.description || '';
                return `<li><b>${rec}</b><br><span style='font-size:90%'>${desc}</span></li>`;
            } else {
                return `<li>${r}</li>`;
            }
        }).join('')}</ul></div>` +
        `<div class="incident-time">${incident.time}</div>`;
    tabContent.appendChild(div);
    container.appendChild(tabs);
    container.appendChild(tabContent);
    // Save active tab globally
    window.activeIncidentTab = activeIdx;
}

function setSystemHealth(healthy) {
	const el = document.getElementById('system-health');
	if (healthy) {
		el.textContent = 'System Healthy';
		el.classList.remove('faulty');
		el.classList.add('healthy');
	} else {
		el.textContent = 'Fault Detected!';
		el.classList.remove('healthy');
		el.classList.add('faulty');
	}
}

function showIncidentLoading() {
    const container = document.getElementById('incidents-list');
    const loadingDiv = document.createElement('div');
    loadingDiv.className = 'incident-loading';
    loadingDiv.textContent = 'Loading incident details...';
    container.innerHTML = '';
    container.appendChild(loadingDiv);
}

async function callAgenticPipeline(sensorData) {
    try {
        const response = await fetch('/rag/analyze', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(sensorData)
        });
        if (!response.ok) throw new Error('Backend error');
        return await response.json();
    } catch (e) {
        return {
            fault: 1,
            root_cause: 'Unknown (backend error)',
            recommendations: ['Check backend connection'],
            confidence: 0,
            sources: [],
            incident_id: null
        };
    }
}

function setIncidentDetailsFromBackend(incident) {
    if (incident && typeof incident.fault !== 'undefined') {
        let faultLabel;
        const noFaultValues = [undefined, null, '', 0, '0', 'None', 'none', false];
        if (noFaultValues.includes(incident.fault)) {
            faultLabel = 'Fault: None';
        } else if (typeof incident.fault === 'string' && incident.fault.trim().toLowerCase() === 'none') {
            faultLabel = 'Fault: None';
        } else {
            faultLabel = `Fault: ${incident.fault}`;
        }
        incidents.push({
            fault: faultLabel,
            rootCause: incident.root_cause || 'N/A',
            recommendations: incident.recommendations && incident.recommendations.length ? incident.recommendations : ['N/A'],
            time: new Date().toLocaleString(),
            confidence: incident.confidence,
            sources: incident.sources,
            incident_id: incident.incident_id
        });
    }
    renderIncidents();
}

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

document.addEventListener('DOMContentLoaded', () => {
	initGraph();
	setSystemHealth(true);
	renderIncidents();
});
