# Reasoner AI Platform - Full UI

A minimalistic AI-powered analysis platform with desktop and mobile support.

## Features

### Core Features
- **Login/Register** - Secure authentication with protected routes
- **Project Management** - Google Drive cascaded folder structure
- **Chat Interface** - AI assistant with file analysis capabilities
- **Smart Context Toggle** - Auto-brief + handoff at 90% capacity
- **Outcomes Panel** - Reports, previews, and execution steps
- **Share & Copy** - For chat messages and outcomes
- **Timestamps** - Full date/time display for all items

### Smart Context Feature
The Smart Context toggle provides:
- **Auto-brief**: Automatically summarizes conversation context
- **Capacity Monitoring**: Real-time context usage tracking
- **Auto-handoff**: Creates new session at 90% capacity
- **Visual Indicator**: Progress bar with color-coded status

## Termux Build Command

### Quick Build
```bash
# Copy and paste this entire command in Termux
cd ~/blank-app/frontend && npm install && npm run build
```

### Full Build Script
Save this as `build.sh` and run `bash build.sh`:

```bash
#!/bin/bash
set -e

echo "=========================================="
echo "  Reasoner AI Platform - Full UI Build"
echo "=========================================="

cd ~/blank-app/frontend

echo "[1/3] Installing dependencies..."
npm install 2>&1 | grep -v "deprecated" || true

echo "[2/3] Building production bundle..."
npm run build

echo "[3/3] Build complete!"
echo ""
echo "Output: $(pwd)/dist"
echo ""
echo "Deploy with:"
echo "  npx surge dist/"
echo "  npx netlify deploy --prod --dir=dist"
```

### One-Liner Command
```bash
cd ~/blank-app/frontend && npm i && npm run build && echo "Build complete! Output: $(pwd)/dist"
```

## Project Structure

```
frontend/src/
├── components/
│   ├── ChatInputV2.tsx        # Chat input with + menu
│   ├── ChatInterfaceV2.tsx    # Main chat interface
│   ├── ChatMessage.tsx        # Message bubble with copy/share
│   ├── OutcomesPanel.tsx      # Reports/previews/steps panel
│   ├── ProjectSidebar.tsx     # Projects sidebar with Google Drive
│   ├── SmartContextToggle.tsx # Smart context toggle UI
│   └── mobile/                # Mobile components
│       ├── MobileChat.tsx
│       ├── MobileNav.tsx
│       ├── MobileOutcomes.tsx
│       ├── MobileProjects.tsx
│       └── MobileSettings.tsx
├── context/
│   └── AuthContext.tsx        # Authentication state
├── pages/
│   ├── Login.tsx              # Login/Register page
│   └── ...
└── App.tsx                    # Main app with routing
```

## UI Layout

### Desktop (3-Panel)
```
┌─────────────┬──────────────────┬─────────────┐
│  Projects   │   Chat Header    │  Outcomes   │
│  Sidebar    │   - Date         │   Panel     │
│             │                  │             │
│ [+] New Chat│ Smart Context    │ [Reports]   │
│ ▼ Project 1 │   Toggle         │ [Previews]  │
│   Chat 1    │                  │ [Steps]     │
│   Chat 2    │ Chat Messages    │             │
│ ▶ Project 2 │ - Copy/Share     │ Outcome 1   │
│             │ - Timestamp      │   [Copy]    │
│ Google Drive│                  │   [Share]   │
│ Connected   │ Input [+] [Send] │   [Download]│
│             │                  │             │
│ Settings    │                  │             │
│ Sign Out    │                  │             │
└─────────────┴──────────────────┴─────────────┘
```

### Mobile (Bottom Navigation)
```
┌─────────────────────┐
│ [+] Projects        │
│ ▼ Project 1         │
│   Chat 1 - 5m ago   │
│ Google Drive        │
├─────────────────────┤
│ Smart Context       │
│   Toggle            │
├─────────────────────┤
│ [Chat] [Outcomes]   │
│ [Projects][Settings]│
└─────────────────────┘
```

## API Integration

The Smart Context toggle connects to:
- `GET /sessions/{token}/capacity` - Get current capacity
- `PATCH /sessions/{token}/settings` - Update toggle state
- `POST /sessions/{token}/messages` - Send message (with handoff detection)

## Environment Variables

```bash
VITE_API_URL=https://blank-app-qc0o.onrender.com
VITE_FRONTEND_URL=https://your-frontend-url.com
```

## Deployment

### Surge.sh
```bash
cd dist && npx surge
```

### Netlify
```bash
npx netlify deploy --prod --dir=dist
```

### Render
Connect GitHub repo and set build command: `npm run build`

## License
MIT
