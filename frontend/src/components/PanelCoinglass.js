import React, { useEffect, useState } from 'react';
import { fetchOpenInterest, fetchFundingRate, fetchWhaleTracker } from '../api';

const PanelCoinglass = ({ symbol }) => {
  const [oi, setOi] = useState(null);
  const [funding, setFunding] = useState(null);
  const [whale, setWhale] = useState(null);

  useEffect(() => {
    fetchOpenInterest(symbol).then(setOi);
    fetchFundingRate(symbol).then(setFunding);
    fetchWhaleTracker().then(setWhale);
  }, [symbol]);

  return (
    <div className="panel">
      <h3>Coinglass Data</h3>
      <div>
        <h4>Open Interest</h4>
        {oi ? <pre>{JSON.stringify(oi.slice(0, 2), null, 2)}</pre> : 'Memuat...'}
      </div>
      <div>
        <h4>Funding Rate</h4>
        {funding ? <pre>{JSON.stringify(funding.slice(0, 2), null, 2)}</pre> : 'Memuat...'}
      </div>
      <div>
        <h4>Whale Tracker</h4>
        {whale ? <pre>{JSON.stringify(whale.slice(0, 2), null, 2)}</pre> : 'Memuat...'}
      </div>
    </div>
  );
};

export default PanelCoinglass;
