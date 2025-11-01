# Photo Match - Foto Upload App

Een React web applicatie met FastAPI backend voor het uploaden van foto's. De app werkt op mobiele telefoons en toont de geüploade foto's.

## Features

- Upload foto's via web interface
- Mobiel-vriendelijke interface
- Camera integratie op mobiele apparaten
- Preview van geselecteerde foto
- Toon geüploade foto (sent_original.png)
- FastAPI backend die de React app serveert

## Installatie

### 1. Python Dependencies

```bash
pip install -r requirements.txt
```

### 2. React Dependencies

```bash
npm install
```

## Development

Voor development kun je de React dev server en FastAPI apart draaien:

### Terminal 1 - React Dev Server
```bash
npm start
```

### Terminal 2 - FastAPI Backend
```bash
python main.py
```

De React dev server draait op http://localhost:3000 en gebruikt proxy naar FastAPI op poort 8080.

## Production

Voor production moet je eerst de React app builden en dan de FastAPI server starten:

### 1. Build de React App
```bash
npm run build
```

### 2. Start de FastAPI Server
```bash
python main.py
```

De applicatie is nu beschikbaar op **http://localhost:8080**

## Gebruik

1. Open http://localhost:8080 in je browser (of op je telefoon als je op hetzelfde netwerk zit)
2. Klik op "Kies een foto" om een foto te selecteren
3. Op mobiel kun je direct een foto maken met de camera
4. Bekijk de preview en klik op "Upload Foto"
5. De foto wordt opgeslagen als `sent_original.png` in de huidige folder
6. De geüploade foto wordt direct getoond op de pagina

## API Endpoints

- `POST /api/upload` - Upload een foto
- `GET /api/photo` - Haal de opgeslagen foto op
- `GET /` - Serveer de React app

## Toegang vanaf Telefoon

Om de app vanaf je telefoon te gebruiken:

1. Zorg dat je telefoon en computer op hetzelfde WiFi netwerk zitten
2. Vind je computer's lokale IP adres:
   - Mac: `ifconfig | grep "inet " | grep -v 127.0.0.1`
   - Linux: `hostname -I`
   - Windows: `ipconfig`
3. Open op je telefoon: `http://[JE-IP-ADRES]:8080`
   - Bijvoorbeeld: `http://192.168.1.100:8080`

## Structuur

```
photo_match/
├── main.py                 # FastAPI backend
├── requirements.txt        # Python dependencies
├── package.json           # Node.js dependencies
├── public/
│   └── index.html        # HTML template
├── src/
│   ├── index.js          # React entry point
│   ├── index.css         # Global styles
│   ├── App.js            # Main React component
│   └── App.css           # App styles
└── build/                # Production build (na npm run build)
```

## Foto Opslag

Geüploade foto's worden opgeslagen als `sent_original.png` in de root folder van het project.
