import React, { useEffect, useState } from 'react';
import { fetchAI } from '../api';

const PanelAI = ({ symbol }) => {
  const [analysis, setAnalysis] = useState(null);

  useEffect(() => {
    fetchAI(symbol).then(setAnalysis);
  }, [symbol]);

  return (
    <div className="panel">
      <h3>AI Analysis</h3>
      {analysis ? (
        <div>
          <p>Score: {analysis.score}</p>
          <p>Rekomendasi: <strong>{analysis.recommendation}</strong></p>
          <ul>
            {analysis.signals.map((s, idx) => <li key={idx}>{s}</li>)}
          </ul>
        </div>
      ) : (
        <p>Memuat...</p>
      )}
    </div>
  );
};

export default PanelAI;
