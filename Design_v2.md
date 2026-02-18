# Reasoner AI Platform - UI Redesign v2

## Layout Structure

### Desktop Layout (3-Column Split)

```
┌─────────────────┬──────────────────────────┬─────────────────┐
│                 │                          │                 │
│   LEFT PANEL    │      CENTER PANEL        │  RIGHT PANEL    │
│   (Sidebar)     │      (Chat Area)         │  (Outcomes)     │
│                 │                          │                 │
│  ┌───────────┐  │  ┌──────────────────┐   │  ┌───────────┐  │
│  │ Projects  │  │  │  Chat Header     │   │  │  Reports  │  │
│  │ (Google   │  │  │  - Project name  │   │  │  Previews │  │
│  │  Drive)   │  │  └──────────────────┘   │  │  Steps    │  │
│  │           │  │                         │  │           │  │
│  │ ▼ Project1│  │  ┌──────────────────┐   │  │           │  │
│  │   Chat 1  │  │  │                  │   │  │           │  │
│  │   Chat 2  │  │  │  Chat Messages   │   │  │           │  │
│  │ ▶ Project2│  │  │                  │   │  │           │  │
│  │ ▶ Project3│  │  │                  │   │  │           │  │
│  │           │  │  └──────────────────┘   │  │           │  │
│  │           │  │                         │  │           │  │
│  │           │  │  ┌──────────────────┐   │  │           │  │
│  │           │  │  │  Chat Input      │   │  │           │  │
│  │           │  │  │  [+] Type... [^] │   │  │           │  │
│  │           │  │  └──────────────────┘   │  │           │  │
│  │           │  │                         │  │           │  │
│  ├───────────┤  │                         │  │           │  │
│  │ Google    │  │                         │  │           │  │
│  │ Drive     │  │                         │  │           │  │
│  │ Connector │  │                         │  │           │  │
│  ├───────────┤  │                         │  │           │  │
│  │ Settings  │  │                         │  │           │  │
│  └───────────┘  │                         │  └───────────┘  │
│                 │                         │                 │
└─────────────────┴─────────────────────────┴─────────────────┘
```

### Mobile Layout (Single Column with Tabs)

```
┌─────────────────────────┐
│  Header - Project Name  │
├─────────────────────────┤
│  [Chat] [Outcomes]      │
├─────────────────────────┤
│                         │
│     Chat / Outcomes     │
│       (Tab Content)     │
│                         │
├─────────────────────────┤
│  [+] Type message...[^] │
├─────────────────────────┤
│  [Projects] [Settings]  │
└─────────────────────────┘
```

## Panel Specifications

### Left Panel (Sidebar) - 280px fixed

**Projects Section (Collapsible Tree)**
- Google Drive cascaded folder structure
- Click project to select
- Expand/collapse chevrons
- Selected project highlighted
- Chat history appears under selected project

**Google Drive Connector Button**
- Located at bottom of sidebar, above Settings
- Icon: Cloud/Link icon
- Text: "Connect Google Drive"
- Status indicator when connected

**Settings Button**
- Very bottom of sidebar
- Icon: Gear icon
- Text: "Settings"

### Center Panel (Chat) - Flexible width

**Chat Header**
- Selected project name
- Connection status
- Menu options

**Chat Messages Area**
- User messages (right-aligned, gray bg)
- AI messages (left-aligned, white bg with border)
- Timestamps
- No emojis - only icons/text

**Chat Input**
- Plus (+) button on left - opens menu:
  - File attachment (paperclip icon)
  - Camera (camera icon)
  - Microphone (mic icon)
  - Internet search (globe icon)
- Text input field
- Send button (paper plane icon)

### Right Panel (Outcomes) - 350px fixed

**Tabs:**
1. Reports - Generated analysis reports
2. Previews - File previews
3. Steps - Execution steps/log

**Content:**
- Card-based layout
- Expandable sections
- Download/share buttons

## Color Palette

```
Background:    #ffffff (white)
Sidebar BG:    #f8f9fa (light gray)
Border:        #e5e7eb (gray-200)
Text Primary:  #111827 (gray-900)
Text Secondary:#6b7280 (gray-500)
Accent:        #4f46e5 (indigo-600)
Accent Hover:  #4338ca (indigo-700)
Success:       #10b981 (emerald-500)
Warning:       #f59e0b (amber-500)
Error:         #ef4444 (red-500)
```

## Typography

- Font: Inter, system-ui, sans-serif
- Base: 14px
- Headings: 16-20px, font-weight 600
- Body: 14px, font-weight 400
- Small: 12px, font-weight 400

## Components

### Project Tree Item
```
[▼] [Folder Icon] Project Name
    [Chat Icon] Chat Title
    [Chat Icon] Chat Title
[▶] [Folder Icon] Project Name
```

### Chat Message
```
User Message:
┌────────────────────────┐
│ Message content        │
│ [File.png 2MB]         │
│                2:30 PM │
└────────────────────────┘

AI Message:
┌────────────────────────┐
│ [Bot Icon]             │
│ Analysis complete.     │
│ Found 3 issues.        │
│                2:31 PM │
└────────────────────────┘
```

### Chat Input with + Menu
```
┌────────────────────────────────────────┐
│ [+] [Type a message...    ] [Send]     │
└────────────────────────────────────────┘

+ Menu Open:
┌─────────────┐
│ [File]      │
│ [Camera]    │
│ [Mic]       │
│ [Internet]  │
└─────────────┘
```

### Outcome Card
```
┌─────────────────────────────┐
│ [Icon] Report Title    [v]  │
├─────────────────────────────┤
│ Summary content...          │
│                             │
│ [Download] [Share]          │
└─────────────────────────────┘
```

## Interactions

### Desktop
- Sidebar resizable (min 240px, max 320px)
- Right panel collapsible
- Drag and drop files anywhere in chat area
- Keyboard shortcuts:
  - Cmd/Ctrl + Enter: Send
  - Esc: Close menus
  - Cmd/Ctrl + B: Toggle sidebar

### Mobile
- Bottom navigation: Projects, Chat, Outcomes, Settings
- Swipe between tabs
- Full-screen modals for menus
- Pull to refresh

## Animations

- Sidebar slide: 200ms ease-out
- Message appear: 150ms fade + 5px slide up
- Menu open: 100ms scale + fade
- Panel collapse: 250ms ease-in-out
- Loading states: Pulse animation
