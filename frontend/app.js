// =============================================
// AI Maintenance Engineer — Dashboard App
// =============================================

// --- Theme colors (match CSS variables) ---
const COLORS = {
	bg: '#111827',
	card: '#1a1f2e',
	accent: '#3b82f6',
	success: '#10b981',
	danger: '#ef4444',
	warning: '#f59e0b',
	text: '#f1f5f9',
	muted: '#64748b',
	grid: 'rgba(255,255,255,0.04)',
};


// --- Debug Pipeline Integration ---
let lastSensorData = null;

function setLastSensorData(data) {
	lastSensorData = data;
}

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
	btn.textContent = '\u{1F50D} Debug Pipeline';
}

function showDebugModal(snapshots) {
	const modal = document.getElementById('debug-modal');
	const content = document.getElementById('debug-modal-content');
	if (!snapshots || !snapshots.length) {
		content.textContent = 'No debug data.';
	} else {
		content.innerHTML = snapshots.map((snap, idx) =>
			`<div style="margin-bottom:1rem;"><b style="color:${COLORS.accent}">Stage ${idx + 1}:</b><pre>${JSON.stringify(snap, null, 2)}</pre></div>`
		).join('');
	}
	modal.style.display = 'flex';
}

document.addEventListener('DOMContentLoaded', () => {
	const modal = document.getElementById('debug-modal');
	const closeBtn = document.getElementById('close-debug-modal');
	if (closeBtn) closeBtn.onclick = () => { modal.style.display = 'none'; };
	const debugBtn = document.getElementById('debug-btn');
	if (debugBtn) debugBtn.onclick = debugPipelineWithLatestData;
});


// --- Patch EventSource for debug data ---
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

const origStartStreaming = startStreaming;
startStreaming = function() {
	origStartStreaming();
	setTimeout(patchEventSourceForDebug, 100);
};


// --- Sensor ID mapper ---
function getSafeId(sensor) {
	return {
		'Air temperature [K]': 'sensor-graph-Air-temperature-K',
		'Process temperature [K]': 'sensor-graph-Process-temperature-K',
		'Rotational speed [rpm]': 'sensor-graph-Rotational-speed-rpm',
		'Torque [Nm]': 'sensor-graph-Torque-Nm',
		'Tool wear [min]': 'sensor-graph-Tool-wear-min',
	}[sensor];
}


// --- Streaming State ---
let streaming = false;
let intervalId = null;

const sensors = [
	'Air temperature [K]',
	'Process temperature [K]',
	'Rotational speed [rpm]',
	'Torque [Nm]',
	'Tool wear [min]'
];


// --- Mock Data Generators ---
function generateSensorData() {
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

function generateFaultySensorData() {
	return {
		'Air temperature [K]': 310,
		'Process temperature [K]': 320,
		'Rotational speed [rpm]': 2100,
		'Torque [Nm]': 49,
		'Tool wear [min]': 199,
		'Type': 1
	};
}


// --- Plotly Live Graphs ---
let time = 0;
let graphData = {};

function initGraph() {
	time = 0;
	sensors.forEach(sensor => {
		graphData[sensor] = { x: [], y: [] };
		Plotly.newPlot(
			getSafeId(sensor),
			[{ x: [], y: [], name: sensor, mode: 'lines', line: { width: 2, color: COLORS.accent, shape: 'spline' } }],
			{
				margin: { t: 8, l: 28, r: 8, b: 24 },
				showlegend: false,
				xaxis: {
					title: '', showticklabels: false, showgrid: false, zeroline: false,
					titlefont: { color: COLORS.muted, size: 9 }
				},
				yaxis: {
					title: sensor.replace(/ \[.*\]/, ''), showticklabels: false,
					showgrid: true, gridcolor: COLORS.grid, zeroline: false,
					titlefont: { color: COLORS.muted, size: 9 }
				},
				paper_bgcolor: 'transparent',
				plot_bgcolor: 'transparent',
				height: 72,
				font: { color: COLORS.muted, size: 9 }
			},
			{ displayModeBar: false, responsive: true }
		);
	});
}

function updateGraph(sensorData) {
	time += 1;
	sensors.forEach(sensor => {
		if (!(sensor in sensorData)) return;
		graphData[sensor].x.push(time);
		graphData[sensor].y.push(sensorData[sensor]);
		Plotly.extendTraces(
			getSafeId(sensor),
			{ x: [[time]], y: [[sensorData[sensor]]] },
			[0]
		);
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
	0: 'None', 1: 'TWF', 2: 'HDF', 3: 'PWF', 4: 'OSF', 5: 'RNF',
	'TWF': 'TWF', 'HDF': 'HDF', 'PWF': 'PWF', 'OSF': 'OSF', 'RNF': 'RNF',
	'None': 'None', 'none': 'None', '0': 'None', '': 'None', null: 'None', undefined: 'None'
};


// --- Incidents ---
let incidents = [];

function renderIncidents() {
	const container = document.getElementById('incidents-list');
	const emptyEl = document.getElementById('incident-list-empty');
	if (!container) return;
	container.innerHTML = '';

	const getFaultTypeLabel = (fault) => {
		let val = fault;
		if (typeof val === 'string' && val.startsWith('Fault: ')) val = val.replace(/^Fault: /, '');
		if (typeof val === 'string' && !isNaN(Number(val))) val = Number(val);
		return FAULT_TYPE_MAP.hasOwnProperty(val) ? FAULT_TYPE_MAP[val] : val;
	};

	const isFault = (incident) => {
		const faultVal = getFaultTypeLabel(incident.fault);
		return faultVal && faultVal !== 'None' && faultVal !== 'No Fault' && faultVal !== '0';
	};

	const faultIncidents = incidents.filter(isFault);
	const countCard = document.getElementById('incident-count');
	if (countCard) countCard.textContent = faultIncidents.length;

	if (emptyEl) emptyEl.style.display = incidents.length === 0 ? '' : 'none';

	if (incidents.length === 0) {
		return;
	}

	incidents.slice().reverse().forEach((incident) => {
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
				<div><strong>Root Cause:</strong> ${incident.root_cause || incident.rootCause || 'N/A'}</div>
				<div><strong>Recommendations:</strong>
					<ul>${(incident.recommendations || []).map(r => {
						if (typeof r === 'object' && r !== null) {
							const rec = r.Recommendation || r.recommendation || '';
							const desc = r.Description || r.description || '';
							return `<li><b>${rec}</b><br><span style="font-size:90%;opacity:0.7">${desc}</span></li>`;
						}
						return `<li>${r}</li>`;
					}).join('')}</ul>
				</div>
			</div>
		`;

		card.onclick = () => {
			window.location.href = '/incident.html?id=' + encodeURIComponent(getIncidentId(incident));
		};
		container.appendChild(card);
	});

	try { localStorage.setItem('incidents', JSON.stringify(incidents)); } catch {}
}


// --- System Health ---
function setSystemHealth(healthy) {
	const el = document.getElementById('system-health');
	const streamEl = document.getElementById('stream-status');
	if (el) {
		if (healthy) {
			el.className = 'summary-value healthy';
			el.innerHTML = '\u{1F7E2} Healthy';
		} else {
			el.className = 'summary-value faulty';
			el.innerHTML = '\u{1F534} Fault Detected';
		}
	}
	if (streamEl && streaming) {
		streamEl.innerHTML = '<span class="pulse-dot"></span> Streaming';
	}
}


// --- Loading Indicator ---
function showIncidentLoading() {
	const container = document.getElementById('incidents-list');
	if (!container) return;
	const existing = container.querySelector('.incident-loading');
	if (existing) return;
	const loader = document.createElement('div');
	loader.className = 'incident-loading';
	loader.innerHTML = '<span class="loading-spinner"></span> Analyzing sensor data...';
	container.prepend(loader);
}

function hideIncidentLoading() {
	const container = document.getElementById('incidents-list');
	if (!container) return;
	const existing = container.querySelector('.incident-loading');
	if (existing) existing.remove();
}


// --- Agentic Pipeline Call ---
async function callAgenticPipeline(data) {
	try {
		const resp = await fetch('/analyze', {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify(data)
		});
		const result = await resp.json();
		hideIncidentLoading();
		return result;
	} catch (e) {
		hideIncidentLoading();
		console.error('Pipeline call failed:', e);
		return { fault: 'None', root_cause: 'Pipeline error', recommendations: ['Check backend connectivity'] };
	}
}


// --- Add incident from backend ---
function setIncidentDetailsFromBackend(incident) {
	if (incident && typeof incident.fault !== 'undefined') {
		const noFaultValues = [undefined, null, '', 0, '0', 'None', 'none', false];
		let faultLabel;
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


// --- Utility ---
function getIncidentId(incident) {
	return incident.incident_id || incident.timestamp || incident.time || '';
}


// --- Dashboard Metrics ---
function setupDashboardMetrics() {
	window.updateDashboardMetrics = function(metrics) {
		if (!metrics) return;
		const map = {
			totalRecords: 'metric-total-records',
			normalOps: 'metric-normal-ops',
			failures: 'metric-failures',
			failureRate: 'metric-failure-rate',
			features: 'metric-features',
			failureModes: 'metric-failure-modes'
		};
		for (const [k, id] of Object.entries(map)) {
			if (metrics[k]) {
				const el = document.getElementById(id);
				if (el) el.textContent = metrics[k];
			}
		}
	};

	window.updateModelMetrics = function(metrics) {
		if (!metrics) return;
		const map = {
			accuracy: 'metric-accuracy',
			precision: 'metric-precision',
			recall: 'metric-recall',
			f1: 'metric-f1',
			auc: 'metric-auc',
			model: 'metric-model'
		};
		for (const [k, id] of Object.entries(map)) {
			if (metrics[k]) {
				const el = document.getElementById(id);
				if (el) el.textContent = metrics[k];
			}
		}
	};
}


// --- Dashboard Charts ---
function setupDashboardCharts() {
	if (!window.Plotly) return;

	const chartLayout = {
		paper_bgcolor: 'transparent',
		plot_bgcolor: 'transparent',
		font: { color: COLORS.muted, size: 10 },
	};

	// Feature Correlation Heatmap
	Plotly.newPlot('feature-correlation-chart', [{
		z: [[1,0.85,-0.12,0.08,0.05],[0.85,1,-0.15,0.11,0.07],[-0.12,-0.15,1,-0.72,-0.03],[0.08,0.11,-0.72,1,0.18],[0.05,0.07,-0.03,0.18,1]],
		x: ['Air Temp','Proc Temp','Speed','Torque','Tool Wear'],
		y: ['Air Temp','Proc Temp','Speed','Torque','Tool Wear'],
		type: 'heatmap',
		colorscale: [[0, '#111827'], [0.5, '#1e3a5f'], [1, '#3b82f6']],
		showscale: true,
		colorbar: { tickfont: { color: COLORS.muted, size: 9 }, len: 0.8 }
	}], {
		...chartLayout,
		margin: { t: 15, l: 65, r: 10, b: 45 },
		height: 180,
	}, { displayModeBar: false });

	// Confusion Matrix
	Plotly.newPlot('confusion-matrix-chart', [{
		z: [[8930,78],[100,892]],
		x: ['Normal','Failure'],
		y: ['Normal','Failure'],
		type: 'heatmap',
		colorscale: [[0, '#111827'], [0.5, '#1e3a5f'], [1, '#3b82f6']],
		showscale: false,
		text: [['8930','78'],['100','892']],
		texttemplate: '%{text}',
		textfont: { color: '#fff', size: 12 },
		hoverinfo: 'skip'
	}], {
		...chartLayout,
		margin: { t: 10, l: 65, r: 10, b: 40 },
		height: 120,
	}, { displayModeBar: false });

	// Pipeline Flow Chart
	Plotly.newPlot('pipeline-flow-chart', [{
		x: [39,346,712,685,652,147,111,99,142],
		y: ['Orchestrator','Retrieval','Reasoning','RootCause','Recommend','Verify','Alert','Schedule','IncidentDoc'],
		type: 'bar',
		orientation: 'h',
		marker: {
			color: [
				COLORS.accent, COLORS.accent, COLORS.warning, COLORS.warning,
				COLORS.success, COLORS.accent, COLORS.accent, COLORS.accent, COLORS.accent
			],
			opacity: 0.85
		},
		text: ['39ms','346ms','712ms','685ms','652ms','147ms','111ms','99ms','142ms'],
		textposition: 'auto',
		textfont: { color: '#fff', size: 10 }
	}], {
		...chartLayout,
		margin: { t: 8, l: 90, r: 10, b: 15 },
		height: 120,
		xaxis: { showticklabels: false, showgrid: false, zeroline: false },
		yaxis: { showgrid: false, zeroline: false, color: COLORS.muted, tickfont: { size: 9 } },
	}, { displayModeBar: false });
}


// --- Clear All ---
function clearAllData() {
	time = 0;
	sensors.forEach(sensor => {
		graphData[sensor] = { x: [], y: [] };
	});
	initGraph();
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

	const streamEl = document.getElementById('stream-status');
	if (streamEl) streamEl.innerHTML = '<span class="pulse-dot"></span> Streaming';

	window.eventSource = new EventSource('/stream');
	window.eventSource.onmessage = async function(event) {
		if (!streaming) return;
		let data;
		try {
			data = JSON.parse(event.data.replace(/'/g, '"'));
		} catch (e) {
			try { data = eval('(' + event.data + ')'); } catch (e2) { return; }
		}
		updateGraph(data);
		showIncidentLoading();
		const result = await callAgenticPipeline(data);

		const noFaultValues = [undefined, null, '', 0, '0', 'None', 'none', false];
		let isNoFault = noFaultValues.includes(result.fault) ||
			(typeof result.fault === 'string' && result.fault.trim().toLowerCase() === 'none');

		if (!isNoFault) {
			setSystemHealth(false);
		} else {
			setSystemHealth(true);
		}
		setIncidentDetailsFromBackend(result);
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

	const streamEl = document.getElementById('stream-status');
	if (streamEl) streamEl.innerHTML = '\u{1F534} Stopped';

	if (window.eventSource) {
		window.eventSource.close();
		window.eventSource = null;
	}
}


// --- Event Listeners ---
document.getElementById('start-btn').addEventListener('click', startStreaming);
document.getElementById('stop-btn').addEventListener('click', stopStreaming);
document.getElementById('clear-btn').addEventListener('click', clearAllData);


// --- Init on DOM Ready ---
document.addEventListener('DOMContentLoaded', function() {
	renderIncidents();
	initGraph();
	setSystemHealth(true);
	setupDashboardMetrics();
	setupDashboardCharts();
});