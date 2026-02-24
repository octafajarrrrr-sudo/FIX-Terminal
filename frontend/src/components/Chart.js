import React, { useEffect, useRef } from 'react';
import { createChart } from 'lightweight-charts';

const Chart = ({ symbol }) => {
  const chartContainerRef = useRef();
  const chartRef = useRef();

  useEffect(() => {
    // Data dummy, nantinya bisa diambil dari API
    const initialData = [
      { time: '2023-01-01', open: 45000, high: 46000, low: 44000, close: 45500 },
      { time: '2023-01-02', open: 45500, high: 47000, low: 45000, close: 46800 },
      // tambahkan data lebih banyak
    ];

    chartRef.current = createChart(chartContainerRef.current, {
      width: 800,
      height: 400,
      layout: { backgroundColor: '#ffffff', textColor: '#000' },
    });
    const candlestickSeries = chartRef.current.addCandlestickSeries();
    candlestickSeries.setData(initialData);

    return () => chartRef.current.remove();
  }, []);

  return <div ref={chartContainerRef} />;
};

export default Chart;
