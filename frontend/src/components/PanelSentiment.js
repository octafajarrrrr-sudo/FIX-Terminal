import React, { useEffect, useState } from 'react';
import { fetchSentiment } from '../api';

const PanelSentiment = ({ symbol }) => {
  const [sentiment, setSentiment] = useState(null);

  useEffect(() => {
    fetchSentiment(symbol).then(setSentiment);
  }, [symbol]);

  return (
    <div className="panel">
      <h3>Sentiment Komunitas</h3>
      {sentiment ? (
        <div>
          <p>Sentiment: {sentiment.sentiment}</p>
          <p>Social Volume: {sentiment.social_volume}</p>
        </div>
      ) : (
        <p>Memuat...</p>
      )}
    </div>
  );
};

export default PanelSentiment;
