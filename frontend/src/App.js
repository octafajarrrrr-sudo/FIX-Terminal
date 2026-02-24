import React, { useEffect, useState } from 'react';
import io from 'socket.io-client';
import Chart from './components/Chart';
import PanelAkun from './components/PanelAkun';
import PanelAI from './components/PanelAI';
import PanelCoinglass from './components/PanelCoinglass';
import PanelWhaleAlert from './components/PanelWhaleAlert';
import PanelSentiment from './components/PanelSentiment';
import OrderForm from './components/OrderForm';
import './App.css';

const socket = io('http://localhost:5000');

function App() {
  const [price, setPrice] = useState(null);
  const [symbol] = useState('BTCUSDT');

  useEffect(() => {
    socket.emit('subscribe', symbol);
    socket.on('price', (data) => {
      if (data.symbol === symbol) setPrice(data.price);
    });

    return () => {
      socket.off('price');
    };
  }, [symbol]);

  return (
    <div className="App">
      <header className="App-header">
        <h1>Trading Terminal</h1>
        {price && <div>Harga {symbol}: ${parseFloat(price).toFixed(2)}</div>}
      </header>
      <main className="dashboard">
        <div className="chart-container">
          <Chart symbol={symbol} />
        </div>
        <div className="panels">
          <PanelAkun />
          <PanelCoinglass symbol={symbol} />
          <PanelWhaleAlert />
          <PanelSentiment symbol={symbol} />
          <PanelAI symbol={symbol} />
        </div>
        <div className="order-form">
          <OrderForm symbol={symbol} />
        </div>
      </main>
    </div>
  );
}

export default App;
