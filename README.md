# Trading Terminal

Terminal trading berbasis web yang mengintegrasikan berbagai sumber data:
- **BingX** sebagai broker (paper trading)
- **Coinglass** untuk open interest, funding rate, whale tracker
- **Whale Alert** untuk transaksi besar
- **LunarCrush** untuk sentiment komunitas
- **AI analytics** untuk rekomendasi berdasarkan data fundamental

## Fitur
- Chart candlestick real-time (Lightweight Charts)
- Informasi akun dan posisi dari BingX
- Panel Open Interest, Funding Rate
- Daftar transaksi whale
- Sentiment komunitas
- Rekomendasi AI (bullish/bearish/neutral)
- Place order market/limit

## Cara Menjalankan

### Prasyarat
- Node.js (v16+)
- NPM atau Yarn
- API keys dari layanan yang digunakan

### Backend
1. Masuk ke folder `backend`
2. Salin `.env.example` menjadi `.env` dan isi API keys
3. Jalankan `npm install`
4. Jalankan `node server.js`

### Frontend
1. Masuk ke folder `frontend`
2. Jalankan `npm install`
3. Jalankan `npm start`
4. Buka `http://localhost:3000`

## Struktur Folder
- `backend/` – server Node.js/Express dengan REST API dan WebSocket
- `frontend/` – aplikasi React dengan komponen-komponen

## Kontribusi
Silakan fork repository ini dan buat pull request untuk pengembangan lebih lanjut.
