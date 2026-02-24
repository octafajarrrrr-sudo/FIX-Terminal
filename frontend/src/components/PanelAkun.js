import React, { useEffect, useState } from 'react';
import { fetchAccount } from '../api';

const PanelAkun = () => {
  const [account, setAccount] = useState(null);

  useEffect(() => {
    fetchAccount().then(setAccount);
  }, []);

  return (
    <div className="panel">
      <h3>Akun</h3>
      {account ? (
        <pre>{JSON.stringify(account, null, 2)}</pre>
      ) : (
        <p>Memuat...</p>
      )}
    </div>
  );
};

export default PanelAkun;
