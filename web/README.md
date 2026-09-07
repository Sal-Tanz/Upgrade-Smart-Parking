# Smart Parking Dashboard

Real-time IoT monitoring dashboard for smart parking system.

## Tech Stack

- **Framework**: Next.js 14 (App Router)
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **Icons**: Lucide React
- **Design System**: Dark mode with IoT green accent

## Getting Started

### Install Dependencies

```bash
cd web
npm install
```

### Run Development Server

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

### Build for Production

```bash
npm run build
npm start
```

## Project Structure

```
web/
├── app/                    # Next.js app directory
│   ├── layout.tsx         # Root layout
│   ├── page.tsx           # Dashboard page
│   └── globals.css        # Global styles
├── components/
│   ├── dashboard/         # Dashboard components
│   │   ├── stats-card.tsx
│   │   ├── parking-grid.tsx
│   │   └── event-list.tsx
│   └── layout/            # Layout components
│       ├── sidebar.tsx
│       └── header.tsx
└── lib/                   # Utilities and data
    ├── utils.ts
    └── mock-data.ts
```

## Features

- 🎨 Dark mode dashboard with IoT green accent
- 📊 Real-time parking slot visualization
- 📈 Statistics cards with trends
- 📝 Event logging and monitoring
- 🚗 Vehicle management interface
- 📅 Attendance tracking
- 🔔 Alert system

## Design System

### Color Palette
- **Background**: #0F172A (Slate 900)
- **Card**: #1E293B (Slate 800)
- **Accent**: #22C55E (Green 500)
- **Available**: #22C55E (Green)
- **Occupied**: #EF4444 (Red)
- **Reserved**: #F59E0B (Amber)
- **Unknown**: #6B7280 (Gray)

### Typography
- **Headings**: Inter (700)
- **Body**: Inter (400-500)
- **Mono**: JetBrains Mono (for plate numbers)

## API Integration

The dashboard is designed to integrate with the FastAPI backend:
- REST API: `http://localhost:8000/api/*`
- WebSocket: `ws://localhost:8000/ws/events`

Currently using mock data for development. Replace with actual API calls in production.

## License

MIT
