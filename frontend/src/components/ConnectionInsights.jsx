import { useState, useEffect } from "react";
import { api } from "../api";
import { useAuth } from "../context/AuthContext";

// Pastel color palette matching app aesthetic
const PASTEL_COLORS = [
  "#FFE5F0", // Soft pink (family-like)
  "#E3F2FD", // Soft blue (friends-like)
  "#F3E5F5", // Soft purple (inner-like)
  "#E8F5E9", // Soft green (work-like)
  "#FFF3E0", // Soft orange (custom-like)
  "#F5F5F5", // Soft gray (generic)
  "#E1F5FE", // Soft cyan
  "#FCE4EC", // Soft rose
  "#F1F8E9", // Soft lime
  "#FFF9C4", // Soft yellow
];

const TAG_COLOR_MAP = {
  family: { bg: "#FFE5F0", text: "#8b3a4a" },
  friends: { bg: "#E3F2FD", text: "#275f86" },
  inner: { bg: "#F3E5F5", text: "#5a4a8a" },
  work: { bg: "#E8F5E9", text: "#296857" },
  custom: { bg: "#FFF3E0", text: "#8a5a2e" },
  generic: { bg: "#F5F5F5", text: "#374151" },
};

export default function ConnectionInsights() {
  const { token } = useAuth();
  const [insights, setInsights] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchInsights = async () => {
      if (!token) {
        setError("No authentication token");
        setLoading(false);
        return;
      }
      
      try {
        setLoading(true);
        setError(null);
        const data = await api.getConnectionInsights(token);
        console.log("Connection insights data:", data);
        setInsights(data);
      } catch (err) {
        console.error("Failed to fetch connection insights", err);
        setError(err.message || "Failed to load insights");
        setInsights(null);
      } finally {
        setLoading(false);
      }
    };

    fetchInsights();
  }, [token]);

  if (loading) {
    return (
      <div className="connection-insights">
        <div className="insights-loading">Loading insights...</div>
      </div>
    );
  }

  if (error) {
    console.error("Connection insights error:", error);
    return (
      <div className="connection-insights">
        <h3 className="insights-title">Connection Insights</h3>
        <div className="insights-error" style={{ color: 'var(--text-subtle)', padding: '16px', textAlign: 'center', fontSize: '14px' }}>
          Unable to load insights: {error}
        </div>
      </div>
    );
  }

  if (!insights) {
    return (
      <div className="connection-insights">
        <h3 className="insights-title">Connection Insights</h3>
        <div className="insights-empty">
          <p>No insights available.</p>
        </div>
      </div>
    );
  }

  const { current_connections, max_connections, connection_percentage, tag_distribution } = insights;

  // Calculate SVG circle for connection progress
  const radius = 60;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (connection_percentage / 100) * circumference;

  // Calculate pie chart segments for tags
  let cumulativePercentage = 0;
  const pieSegments = tag_distribution
    .filter(tag => tag.percentage > 0) // Only include tags with percentage > 0
    .map((tag, index) => {
      const startAngle = (cumulativePercentage / 100) * 360 - 90; // Start from top
      const endAngle = ((cumulativePercentage + tag.percentage) / 100) * 360 - 90;
      cumulativePercentage += tag.percentage;

      const startAngleRad = (startAngle * Math.PI) / 180;
      const endAngleRad = (endAngle * Math.PI) / 180;

      const x1 = 100 + 80 * Math.cos(startAngleRad);
      const y1 = 100 + 80 * Math.sin(startAngleRad);
      const x2 = 100 + 80 * Math.cos(endAngleRad);
      const y2 = 100 + 80 * Math.sin(endAngleRad);

      const largeArcFlag = tag.percentage > 50 ? 1 : 0;

      // Handle full circle case
      const pathData = tag.percentage >= 100
        ? `M 100 100 L 100 20 A 80 80 0 1 1 99.9 20 Z`
        : `M 100 100 L ${x1.toFixed(2)} ${y1.toFixed(2)} A 80 80 0 ${largeArcFlag} 1 ${x2.toFixed(2)} ${y2.toFixed(2)} Z`;

      const colorScheme = tag.color_scheme || "generic";
      const colorInfo = TAG_COLOR_MAP[colorScheme] || TAG_COLOR_MAP.generic;

      return {
        ...tag,
        pathData,
        color: colorInfo.bg,
        textColor: colorInfo.text,
      };
    });

  return (
    <div className="connection-insights">
      <h3 className="insights-title">Connection Insights</h3>
      
      {/* Connection Progress Circle - Always show */}
      <div className="insights-section">
        <div className="connection-progress-container">
          <svg className="connection-progress-circle" viewBox="0 0 140 140">
            <circle
              cx="70"
              cy="70"
              r={radius}
              fill="none"
              stroke="var(--color-divider)"
              strokeWidth="12"
            />
            <circle
              cx="70"
              cy="70"
              r={radius}
              fill="none"
              stroke="var(--olive-primary)"
              strokeWidth="12"
              strokeDasharray={circumference}
              strokeDashoffset={offset}
              strokeLinecap="round"
              transform="rotate(-90 70 70)"
              className="connection-progress-fill"
            />
          </svg>
          <div className="connection-progress-text">
            <div className="progress-percentage">{Math.round(connection_percentage)}%</div>
            <div className="progress-label">
              {current_connections} / {max_connections}
            </div>
          </div>
        </div>
      </div>

      {/* Tag Distribution Pie Chart */}
      {tag_distribution.length > 0 ? (
        <div className="insights-section">
          <h4 className="insights-subtitle">Tag Distribution</h4>
          <div className="tag-pie-container">
            <svg className="tag-pie-chart" viewBox="0 0 200 200">
              {pieSegments.map((segment, index) => (
                <path
                  key={segment.tag_id}
                  d={segment.pathData}
                  fill={segment.color}
                  stroke="var(--surface-color)"
                  strokeWidth="2"
                  className="pie-segment"
                />
              ))}
            </svg>
            <div className="tag-legend">
              {tag_distribution.map((tag) => {
                const colorScheme = tag.color_scheme || "generic";
                const colorInfo = TAG_COLOR_MAP[colorScheme] || TAG_COLOR_MAP.generic;
                return (
                  <div key={tag.tag_id} className="legend-item">
                    <div
                      className="legend-color"
                      style={{ backgroundColor: colorInfo.bg }}
                    />
                    <span className="legend-label">{tag.tag_name}</span>
                    <span className="legend-percentage">{tag.percentage}%</span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      ) : (
        <div className="insights-section">
          <div className="insights-empty">
            <p>No tags assigned yet. Tag your connections to see distribution.</p>
          </div>
        </div>
      )}
    </div>
  );
}
