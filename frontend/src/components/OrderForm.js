import React, { useState } from 'react';
import { placeOrder } from '../api';

const OrderForm = ({ symbol }) => {
  const [side, setSide] = useState('buy');
  const [qty, setQty] = useState('');
  const [type, setType] = useState('market');

  const handleSubmit = async (e) => {
    e.preventDefault();
    const order = {
      symbol,
      qty: parseFloat(qty),
      side,
      type,
      time_in_force: 'gtc'
    };
    const result = await placeOrder(order);
    alert(`Order placed: ${JSON.stringify(result)}`);
  };

  return (
    <form onSubmit={handleSubmit} className="order-form">
      <h3>Place Order</h3>
      <select value={side} onChange={(e) => setSide(e.target.value)}>
        <option value="buy">Buy</option>
        <option value="sell">Sell</option>
      </select>
      <input
        type="number"
        value={qty}
        onChange={(e) => setQty(e.target.value)}
        placeholder="Quantity"
        step="any"
        required
      />
      <select value={type} onChange={(e) => setType(e.target.value)}>
        <option value="market">Market</option>
        <option value="limit">Limit</option>
      </select>
      <button type="submit">Place Order</button>
    </form>
  );
};

export default OrderForm;
