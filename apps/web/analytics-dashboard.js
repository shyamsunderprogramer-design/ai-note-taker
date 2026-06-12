/**
 * Analytics Dashboard JavaScript
 * Phase 2 Task #31 - Graph Analytics Dashboard
 */

var API_BASE = typeof API_BASE !== 'undefined' ? API_BASE : 'http://127.0.0.1:8000';
const DEFAULT_USER_ID = 'default';

// State
let skillChart = null;

// Initialize
document.addEventListener('DOMContentLoaded', async () => {
  await loadDashboardData();
  setupEventListeners();
});

// Setup event listeners
function setupEventListeners() {
  const skillSelect = document.getElementById('skillSelect');
  skillSelect?.addEventListener('change', (e) => {
    loadSkillProgression(e.target.value);
  });
}

// Load all dashboard data
async function loadDashboardData() {
  try {
    // Load dashboard summary
    const summaryResponse = await fetch(`${API_BASE}/analytics/dashboard/${DEFAULT_USER_ID}`);
    const summary = await summaryResponse.json();

    if (summary.error) {
      throw new Error(summary.error);
    }

    // Update summary cards
    updateSummaryCards(summary.summary);

    // Load performance trends
    await loadPerformanceTrends();

    // Load skill progression for first skill
    const firstSkill = document.getElementById('skillSelect')?.value || 'React';
    await loadSkillProgression(firstSkill);

    // Load interview calendar
    await loadInterviewCalendar();

    // Load topic network
    await loadTopicNetwork();

    // Load company comparison
    await loadCompanyComparison();

    // Show content, hide loading
    document.getElementById('loadingState').style.display = 'none';
    document.getElementById('dashboardContent').style.display = 'block';

  } catch (error) {
    console.error('[Analytics] Error loading dashboard:', error);
    document.getElementById('loadingState').innerHTML = `
      <div style="text-align: center; padding: 40px;">
        <p>Error loading analytics: ${error.message}</p>
        <p style="color: var(--text-secondary);">Make sure the backend is running</p>
      </div>
    `;
  }
}

// Update summary cards
function updateSummaryCards(summary) {
  document.getElementById('totalInterviews').textContent = summary.total_interviews || 0;
  document.getElementById('currentStreak').textContent = summary.current_streak || 0;
  document.getElementById('totalSkills').textContent = summary.total_skills || 0;
  document.getElementById('improvingCount').textContent = summary.improving_count || 0;
}

// Load skill progression chart
async function loadSkillProgression(skill) {
  try {
    const response = await fetch(`${API_BASE}/analytics/skill-progression/${DEFAULT_USER_ID}?skill=${encodeURIComponent(skill)}&months=6`);
    const data = await response.json();

    if (data.error) {
      throw new Error(data.error);
    }

    const ctx = document.getElementById('skillChart').getContext('2d');

    // Prepare data
    const labels = data.data_points?.map(d => d.month) || [];
    const confidenceData = data.data_points?.map(d => d.confidence * 100) || [];
    const mentionsData = data.data_points?.map(d => d.mentions) || [];

    // Destroy existing chart
    if (skillChart) {
      skillChart.destroy();
    }

    // Create new chart
    skillChart = new Chart(ctx, {
      type: 'line',
      data: {
        labels: labels,
        datasets: [
          {
            label: 'Confidence (%)',
            data: confidenceData,
            borderColor: '#3b82f6',
            backgroundColor: 'rgba(59, 130, 246, 0.1)',
            tension: 0.4,
            fill: true,
            yAxisID: 'y'
          },
          {
            label: 'Mentions',
            data: mentionsData,
            borderColor: '#10b981',
            backgroundColor: 'rgba(16, 185, 129, 0.1)',
            tension: 0.4,
            fill: true,
            yAxisID: 'y1'
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
          mode: 'index',
          intersect: false
        },
        plugins: {
          legend: {
            display: true,
            position: 'top'
          },
          tooltip: {
            callbacks: {
              afterLabel: function(context) {
                const point = data.data_points[context.dataIndex];
                if (point && point.sample_questions?.length > 0) {
                  return 'Q: ' + point.sample_questions[0].substring(0, 50) + '...';
                }
                return '';
              }
            }
          }
        },
        scales: {
          y: {
            type: 'linear',
            display: true,
            position: 'left',
            min: 0,
            max: 100
          },
          y1: {
            type: 'linear',
            display: true,
            position: 'right',
            grid: {
              drawOnChartArea: false
            }
          }
        }
      }
    });

  } catch (error) {
    console.error('[Analytics] Error loading skill progression:', error);
  }
}

// Load performance trends
async function loadPerformanceTrends() {
  try {
    const response = await fetch(`${API_BASE}/analytics/performance-trends/${DEFAULT_USER_ID}`);
    const data = await response.json();

    if (data.error) {
      throw new Error(data.error);
    }

    const container = document.getElementById('trendsList');
    if (!container) return;

    // Combine all trends
    const allTrends = [
      ...(data.improving || []).map(s => ({ ...s, status: 'improving' })),
      ...(data.declining || []).map(s => ({ ...s, status: 'declining' })),
      ...(data.stable || []).map(s => ({ ...s, status: 'stable' }))
    ];

    // Sort by absolute trend
    allTrends.sort((a, b) => Math.abs(b.trend) - Math.abs(a.trend));

    // Display top 10
    const topTrends = allTrends.slice(0, 10);

    container.innerHTML = topTrends.map(skill => `
      <div class="trend-item">
        <span class="trend-name">${skill.name}</span>
        <div class="trend-value">
          <span class="trend-arrow ${skill.status}">
            ${skill.status === 'improving' ? '↑' : skill.status === 'declining' ? '↓' : '→'}
          </span>
          <span>${skill.current_confidence.toFixed(2)}</span>
          <span style="color: ${skill.status === 'improving' ? '#10b981' : skill.status === 'declining' ? '#ef4444' : '#888'}; font-size: 12px;">
            ${skill.trend > 0 ? '+' : ''}${skill.trend.toFixed(2)}
          </span>
        </div>
      </div>
    `).join('');

  } catch (error) {
    console.error('[Analytics] Error loading performance trends:', error);
  }
}

// Load interview calendar
async function loadInterviewCalendar() {
  try {
    const response = await fetch(`${API_BASE}/analytics/interview-calendar/${DEFAULT_USER_ID}?months=6`);
    const data = await response.json();

    if (data.error) {
      throw new Error(data.error);
    }

    const container = document.getElementById('calendarHeatmap');
    if (!container) return;

    // Generate calendar days (simplified - last 180 days)
    const days = [];
    const today = new Date();
    const activity = data.daily_activity || {};

    for (let i = 180; i >= 0; i--) {
      const date = new Date(today);
      date.setDate(date.getDate() - i);
      const dateStr = date.toISOString().split('T')[0];
      const count = activity[dateStr] || 0;

      let level = 0;
      if (count === 1) level = 1;
      else if (count === 2) level = 2;
      else if (count === 3) level = 3;
      else if (count >= 4) level = 4;

      days.push(`<div class="calendar-day level-${level}" title="${dateStr}: ${count} interviews"></div>`);
    }

    container.innerHTML = days.join('');

  } catch (error) {
    console.error('[Analytics] Error loading interview calendar:', error);
  }
}

// Load topic network
async function loadTopicNetwork() {
  try {
    const response = await fetch(`${API_BASE}/analytics/topic-network/${DEFAULT_USER_ID}?min_connections=2`);
    const data = await response.json();

    if (data.error) {
      throw new Error(data.error);
    }

    const container = document.getElementById('networkGraph');
    if (!container) return;

    // Clear existing
    container.innerHTML = '';

    // Setup D3 force simulation
    const width = container.clientWidth || 600;
    const height = 400;

    const svg = d3.select('#networkGraph')
      .append('svg')
      .attr('width', width)
      .attr('height', height);

    const nodes = data.nodes || [];
    const links = data.edges || [];

    if (nodes.length === 0) {
      container.innerHTML = '<div style="text-align: center; padding: 40px; color: var(--text-secondary);">Not enough topic data yet</div>';
      return;
    }

    // Color scale by group
    const color = d3.scaleOrdinal()
      .domain(['frontend', 'backend', 'algorithms', 'system_design', 'devops', 'languages', 'other'])
      .range(['#60a5fa', '#34d399', '#fbbf24', '#a78bfa', '#f87171', '#22d3ee', '#9ca3af']);

    // Force simulation
    const simulation = d3.forceSimulation(nodes)
      .force('link', d3.forceLink(links).id(d => d.id).distance(100))
      .force('charge', d3.forceManyBody().strength(-300))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .force('collision', d3.forceCollide().radius(d => d.size || 10));

    // Draw links
    const link = svg.append('g')
      .selectAll('line')
      .data(links)
      .join('line')
      .attr('class', 'network-link')
      .attr('stroke-width', d => Math.sqrt(d.weight || 1));

    // Draw nodes
    const node = svg.append('g')
      .selectAll('g')
      .data(nodes)
      .join('g')
      .attr('class', 'network-node')
      .call(d3.drag()
        .on('start', dragstarted)
        .on('drag', dragged)
        .on('end', dragended));

    // Add circles to nodes
    node.append('circle')
      .attr('r', d => d.size || 10)
      .attr('fill', d => color(d.group))
      .attr('stroke', '#fff')
      .attr('stroke-width', 1.5);

    // Add labels to nodes
    node.append('text')
      .text(d => d.name)
      .attr('x', d => (d.size || 10) + 5)
      .attr('y', 4)
      .attr('font-size', '11px')
      .attr('fill', 'var(--text-primary)')
      .style('pointer-events', 'none');

    // Update positions
    simulation.on('tick', () => {
      link
        .attr('x1', d => d.source.x)
        .attr('y1', d => d.source.y)
        .attr('x2', d => d.target.x)
        .attr('y2', d => d.target.y);

      node.attr('transform', d => `translate(${d.x},${d.y})`);
    });

    // Drag functions
    function dragstarted(event, d) {
      if (!event.active) simulation.alphaTarget(0.3).restart();
      d.fx = d.x;
      d.fy = d.y;
    }

    function dragged(event, d) {
      d.fx = event.x;
      d.fy = event.y;
    }

    function dragended(event, d) {
      if (!event.active) simulation.alphaTarget(0);
      d.fx = null;
      d.fy = null;
    }

    // Add legend
    const legend = svg.append('g')
      .attr('transform', `translate(10, ${height - 100})`);

    const groups = [...new Set(nodes.map(n => n.group))];
    groups.forEach((group, i) => {
      const legendRow = legend.append('g')
        .attr('transform', `translate(0, ${i * 20})`);

      legendRow.append('circle')
        .attr('r', 6)
        .attr('fill', color(group));

      legendRow.append('text')
        .text(group.replace('_', ' '))
        .attr('x', 12)
        .attr('y', 4)
        .attr('font-size', '10px')
        .attr('fill', 'var(--text-secondary)');
    });

  } catch (error) {
    console.error('[Analytics] Error loading topic network:', error);
  }
}

// Load company comparison
async function loadCompanyComparison() {
  try {
    // Get companies from cognitive graph or use defaults
    const companies = ['Google', 'Meta', 'Amazon', 'Netflix', 'Microsoft'];

    const response = await fetch(`${API_BASE}/analytics/company-comparison?companies=${companies.join(',')}`);
    const data = await response.json();

    if (data.error) {
      throw new Error(data.error);
    }

    const container = document.getElementById('companyComparison');
    if (!container) return;

    const categories = data.categories || [];
    const heatmap = data.heatmap || [];

    if (categories.length === 0 || heatmap.length === 0) {
      container.innerHTML = '<div style="text-align: center; padding: 40px; color: var(--text-secondary);">No company comparison data yet</div>';
      return;
    }

    // Create heatmap table
    let html = '<table class="heatmap-table">';

    // Header row
    html += '<tr><th class="heatmap-cell header">Company</th>';
    categories.forEach(cat => {
      html += `<th class="heatmap-cell header">${cat.replace('_', ' ')}</th>`;
    });
    html += '</tr>';

    // Data rows
    heatmap.forEach(row => {
      html += `<tr><td class="heatmap-cell header">${row.company}</td>`;
      row.values.forEach(val => {
        const intensity = Math.min(val.percentage / 50, 1); // Max at 50%
        const bgColor = `rgba(59, 130, 246, ${intensity * 0.8})`;
        html += `<td class="heatmap-cell" style="background: ${bgColor}">${val.count}</td>`;
      });
      html += '</tr>';
    });

    html += '</table>';
    container.innerHTML = html;

  } catch (error) {
    console.error('[Analytics] Error loading company comparison:', error);
  }
}
