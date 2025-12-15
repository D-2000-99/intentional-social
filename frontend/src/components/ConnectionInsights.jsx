import { useState, useEffect } from "react";
import { api } from "../api";
import { useAuth } from "../context/AuthContext";

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
        <h3 className="insights-title">Circle Capacity</h3>
        <div className="insights-error" style={{ color: 'var(--text-subtle)', padding: '16px', textAlign: 'center', fontSize: '14px' }}>
          Unable to load insights: {error}
        </div>
      </div>
    );
  }

  if (!insights) {
    return (
      <div className="connection-insights">
        <h3 className="insights-title">Circle Capacity</h3>
        <div className="insights-empty">
          <p>No insights available.</p>
        </div>
      </div>
    );
  }

  const { current_connections, max_connections, connection_percentage } = insights;

  // Calculate simple donut chart for connection progress
  const centerX = 100;
  const centerY = 100;
  const outerRadius = 80;
  const innerRadius = 50; // Creates donut hole
  
  // Calculate filled portion
  const filledPercentage = connection_percentage;
  const remainingPercentage = 100 - filledPercentage;
  
  // Filled segment
  let filledSegment = null;
  if (filledPercentage > 0) {
    const startAngle = -90; // Start from top
    const endAngle = -90 + (filledPercentage / 100) * 360;

    const startAngleRad = (startAngle * Math.PI) / 180;
    const endAngleRad = (endAngle * Math.PI) / 180;

    const x1 = centerX + outerRadius * Math.cos(startAngleRad);
    const y1 = centerY + outerRadius * Math.sin(startAngleRad);
    const x2 = centerX + outerRadius * Math.cos(endAngleRad);
    const y2 = centerY + outerRadius * Math.sin(endAngleRad);
    const x3 = centerX + innerRadius * Math.cos(endAngleRad);
    const y3 = centerY + innerRadius * Math.sin(endAngleRad);
    const x4 = centerX + innerRadius * Math.cos(startAngleRad);
    const y4 = centerY + innerRadius * Math.sin(startAngleRad);

    const largeArcFlag = filledPercentage > 50 ? 1 : 0;

    const pathData = `M ${x1.toFixed(2)} ${y1.toFixed(2)} 
      A ${outerRadius} ${outerRadius} 0 ${largeArcFlag} 1 ${x2.toFixed(2)} ${y2.toFixed(2)}
      L ${x3.toFixed(2)} ${y3.toFixed(2)}
      A ${innerRadius} ${innerRadius} 0 ${largeArcFlag} 0 ${x4.toFixed(2)} ${y4.toFixed(2)}
      Z`;

    filledSegment = {
      pathData,
      color: "var(--olive-primary)",
    };
  }

  // Remaining unfilled portion
  let remainingSegment = null;
  if (remainingPercentage > 0) {
    const startAngle = -90 + (filledPercentage / 100) * 360;
    const endAngle = -90 + 360;

    const startAngleRad = (startAngle * Math.PI) / 180;
    const endAngleRad = (endAngle * Math.PI) / 180;

    const x1 = centerX + outerRadius * Math.cos(startAngleRad);
    const y1 = centerY + outerRadius * Math.sin(startAngleRad);
    const x2 = centerX + outerRadius * Math.cos(endAngleRad);
    const y2 = centerY + outerRadius * Math.sin(endAngleRad);
    const x3 = centerX + innerRadius * Math.cos(endAngleRad);
    const y3 = centerY + innerRadius * Math.sin(endAngleRad);
    const x4 = centerX + innerRadius * Math.cos(startAngleRad);
    const y4 = centerY + innerRadius * Math.sin(startAngleRad);

    const largeArcFlag = remainingPercentage > 50 ? 1 : 0;

    const pathData = `M ${x1.toFixed(2)} ${y1.toFixed(2)} 
      A ${outerRadius} ${outerRadius} 0 ${largeArcFlag} 1 ${x2.toFixed(2)} ${y2.toFixed(2)}
      L ${x3.toFixed(2)} ${y3.toFixed(2)}
      A ${innerRadius} ${innerRadius} 0 ${largeArcFlag} 0 ${x4.toFixed(2)} ${y4.toFixed(2)}
      Z`;

    remainingSegment = {
      pathData,
      color: "var(--color-divider)",
    };
  }

  return (
    <div className="connection-insights">
      <h3 className="insights-title">Circle Capacity</h3>
      
      {/* Simple Donut Chart */}
      <div className="insights-section">
        <div className="combined-donut-container">
          <svg className="combined-donut-chart" viewBox="0 0 200 200">
            {/* Render remaining unfilled portion first (behind) */}
            {remainingSegment && (
              <path
                d={remainingSegment.pathData}
                fill={remainingSegment.color}
                className="donut-segment"
                opacity="0.3"
              />
            )}
            {/* Render filled portion */}
            {filledSegment && (
              <path
                d={filledSegment.pathData}
                fill={filledSegment.color}
                stroke="var(--surface-color)"
                strokeWidth="2"
                className="donut-segment"
              />
            )}
          </svg>
          <div className="donut-center-text">
            <div className="progress-percentage">{Math.round(connection_percentage)}%</div>
            <div className="progress-label">
              {current_connections} / {max_connections}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
