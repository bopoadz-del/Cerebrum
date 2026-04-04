# Reasoner AI Platform - Technical Specification

## Component Inventory

### shadcn/ui Components (Built-in)

| Component | Purpose | Customization |
|-----------|---------|---------------|
| Button | All buttons | Custom colors, sizes |
| Card | Content containers | Custom shadows, borders |
| Input | Text inputs | Custom focus ring |
| Textarea | Multi-line inputs | Auto-resize |
| Dialog | Modals | Custom animations |
| DropdownMenu | Dropdowns | - |
| Select | Dropdown selects | - |
| Tabs | Tab navigation | Custom indicator |
| Badge | Status labels | Custom colors |
| Avatar | User avatars | - |
| Tooltip | Hover hints | - |
| ScrollArea | Custom scrollbars | - |
| Separator | Dividers | - |
| Skeleton | Loading states | - |
| Sheet | Side panels | For mobile sidebar |
| Toast | Notifications | - |
| Toggle | Switch buttons | - |
| Accordion | Expandable sections | - |

### Custom Components to Build

| Component | Purpose | Location |
|-----------|---------|----------|
| Sidebar | Main navigation | `components/Sidebar.tsx` |
| ChatInterface | AI chat UI | `components/ChatInterface.tsx` |
| ChatMessage | Individual message | `components/ChatMessage.tsx` |
| ChatInput | Message input | `components/ChatInput.tsx` |
| FileUpload | Upload zone | `components/FileUpload.tsx` |
| AnalysisResult | Result display | `components/AnalysisResult.tsx` |
| FormulaCard | Formula item | `components/FormulaCard.tsx` |
| StatCard | Dashboard stat | `components/StatCard.tsx` |
| ModuleHeader | Page header | `components/ModuleHeader.tsx` |
| NavItem | Sidebar item | `components/NavItem.tsx` |

## Animation Implementation Table

| Animation | Library | Implementation Approach | Complexity |
|-----------|---------|------------------------|------------|
| Sidebar slide-in | Framer Motion | `motion.aside` with initial/animate | Low |
| Content fade-in | Framer Motion | `motion.div` with stagger | Low |
| Message appear | Framer Motion | `AnimatePresence` + `motion.div` | Medium |
| Button hover | CSS/Tailwind | `hover:scale-102` transition | Low |
| Card hover | CSS/Tailwind | `hover:shadow-lg` transition | Low |
| Nav item slide | CSS/Tailwind | `hover:pl-5` transition | Low |
| Input focus | CSS/Tailwind | `focus:ring` transition | Low |
| Progress bar | Framer Motion | `motion.div` width animation | Low |
| Number count-up | Custom hook | `useCountUp` with requestAnimationFrame | Medium |
| Chart tooltips | Recharts | Built-in tooltip component | Low |
| Modal open/close | Framer Motion | `AnimatePresence` + scale/opacity | Medium |
| File drop highlight | CSS/React | Dynamic class on drag state | Low |
| Toast notifications | Framer Motion | `AnimatePresence` slide-in | Low |
| Page transitions | Framer Motion | `motion.div` with key-based animate | Medium |
| Skeleton shimmer | CSS | `animate-pulse` or keyframes | Low |

## Animation Library Choices

### Primary: Framer Motion
- **Rationale**: Best React integration, declarative API, AnimatePresence for mount/unmount
- **Use for**: All component animations, page transitions, gesture-based interactions

### Secondary: CSS/Tailwind
- **Rationale**: Performance for simple transitions, no JS overhead
- **Use for**: Hover states, focus states, simple transforms

### Tertiary: Custom Hooks
- **Rationale**: Specific behavior not covered by libraries
- **Use for**: Number counting, scroll-based animations

## Project File Structure

```
/mnt/okcomputer/output/app/
├── public/
│   └── (static assets)
├── src/
│   ├── components/
│   │   ├── ui/              # shadcn components
│   │   ├── Sidebar.tsx
│   │   ├── NavItem.tsx
│   │   ├── ChatInterface.tsx
│   │   ├── ChatMessage.tsx
│   │   ├── ChatInput.tsx
│   │   ├── FileUpload.tsx
│   │   ├── AnalysisResult.tsx
│   │   ├── FormulaCard.tsx
│   │   ├── StatCard.tsx
│   │   └── ModuleHeader.tsx
│   ├── hooks/
│   │   ├── useCountUp.ts
│   │   ├── useSidebar.ts
│   │   └── useChat.ts
│   ├── lib/
│   │   └── utils.ts
│   ├── pages/
│   │   ├── Home.tsx
│   │   ├── SchedulePage.tsx
│   │   ├── AudioPage.tsx
│   │   ├── ArchivePage.tsx
│   │   ├── CadPage.tsx
│   │   ├── PdfPage.tsx
│   │   ├── AnomalyPage.tsx
│   │   ├── ForecastPage.tsx
│   │   ├── DocumentPage.tsx
│   │   ├── IfcPage.tsx
│   │   ├── FormulasPage.tsx
│   │   └── Dashboard.tsx
│   ├── types/
│   │   └── index.ts
│   ├── App.tsx
│   ├── main.tsx
│   └── index.css
├── components.json
├── tailwind.config.js
├── tsconfig.json
└── package.json
```

## Dependencies to Install

### Core (from init)
- React 18+
- TypeScript
- Vite
- Tailwind CSS
- shadcn/ui components

### Additional
```bash
# Animation
npm install framer-motion

# Icons
npm install lucide-react

# Charts (for dashboard)
npm install recharts

# Date formatting
npm install date-fns

# Class utilities (already included)
# clsx, tailwind-merge
```

## Color Configuration (tailwind.config.js)

```javascript
colors: {
  primary: {
    DEFAULT: '#1a1a1a',
    light: '#2d2d2d',
  },
  accent: {
    DEFAULT: '#6366f1',
    hover: '#4f46e5',
  },
  background: {
    primary: '#ffffff',
    secondary: '#f9fafb',
    tertiary: '#f3f4f6',
  },
  text: {
    primary: '#111827',
    secondary: '#6b7280',
    muted: '#9ca3af',
  },
  border: {
    primary: '#e5e7eb',
    secondary: '#d1d5db',
  },
  status: {
    success: '#10b981',
    warning: '#f59e0b',
    error: '#ef4444',
    info: '#3b82f6',
  },
}
```

## Key Implementation Notes

1. **Sidebar State**: Use React Context for collapsed/expanded state
2. **Chat Messages**: Use useState with array, auto-scroll to bottom
3. **File Upload**: Handle drag-drop events, show progress
4. **Responsive**: Mobile-first, use Tailwind breakpoints
5. **Accessibility**: All interactive elements keyboard accessible
6. **Performance**: Use React.memo for message list items
