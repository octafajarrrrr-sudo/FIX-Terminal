import React, { useEffect, useState } from 'react';
import { fetchWhaleAlert } from '../api';

const PanelWhaleAlert = () => {
  const [txs, setTxs] = useState([]);

  useEffect(() => {
    fetchWhaleAlert().then(setTxs);
  }, []);

  return (
    <div className="panel">
      <h3>Whale Alert</h3>
      <ul>
        {txs.slice(0, 5).map((tx, idx) => (
          <li key={idx}>
            {tx.symbol} {tx.amount} (${tx.value}) - {tx.from?.owner || '?'} → {tx.to?.owner || '?'}
          </li>
        ))}
      </ul>
    </div>
  );
};

export default PanelWhaleAlert;
