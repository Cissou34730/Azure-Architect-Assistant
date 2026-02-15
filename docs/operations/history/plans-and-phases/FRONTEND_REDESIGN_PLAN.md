# Frontend Redesign Implementation Plan

**Branch:** `feat/frontend-redesign`  
**Started:** January 24, 2026  
**Status:** In Progress

## Overview

Complete redesign of the Project workspace and AAA assistant UI from 6 confusing tabs to 3 focused views with modern dashboard-style interface inspired by Notion.

## Current Problems

1. **6 tabs** (AAA, Chat, State, Documents, Diagrams, Proposal) with overlapping content
2. **AAA tab** is a massive wall of text with 15+ collapsible sections - overwhelming
3. **Diagrams and ADRs** are hidden in the AAA tab instead of being prominently featured
4. **No clear workflow** - users don't know where to start or what to do next
5. **Poor information hierarchy** - everything has equal visual weight
6. **No visual differentiation** - just gray boxes everywhere

## New Structure

### 3 Main Views

#### 1. 📊 Overview Dashboard (replaces AAA + State)
- Hero metrics at top (requirements count, ADRs, findings, completion %)
- Visual status cards with icons
- Quick actions panel
- Recent activity timeline
- Requirements categorized (Business, Functional, NFR)
- Architecture coverage with mindmap visualization
- WAF assessment as progress rings

#### 2. 💬 Workspace (combines Chat + Documents)
- Split-pane layout: Chat on left, Context panel on right
- Document upload integrated into chat
- Live project state sidebar showing current requirements/assumptions
- Modern message bubbles with agent avatars
- Code syntax highlighting in responses
- Citation chips (clickable to view sources)

#### 3. 📐 Deliverables (replaces Proposal + elevates Diagrams)
- Gallery view for Architecture Diagrams (C4, functional, container)
- ADR library with search/filter
- IaC code viewer with syntax highlighting
- Cost estimates with visual breakdown (charts)
- Downloadable proposal document

---

## Implementation Checklist

### ✅ Phase 1: Foundation (COMPLETED)
- [x] Create `feat/frontend-redesign` branch
- [x] Install dependencies: lucide-react, recharts, react-syntax-highlighter, react-markdown
- [x] Create Card component (Card, CardHeader, CardContent, CardTitle, CardDescription)
- [x] Create Badge component with variants (default, primary, success, warning, error, info)
- [x] Create EmptyState component with icon support
- [x] Create StatCard component with trend indicators
- [x] Create Skeleton components (Skeleton, CardSkeleton, StatCardSkeleton)
- [x] Update common/index.ts barrel export

### 🔄 Phase 2: Overview Dashboard Components (IN PROGRESS)

#### 2.1 Hero Stats Bar
**File:** `frontend/src/features/projects/components/overview/HeroStats.tsx`
- [ ] Display 4 key metrics: Requirements count, ADRs count, Findings count, Monthly cost
- [ ] Use StatCard components
- [ ] Responsive grid layout (4 columns on desktop, 2 on tablet, 1 on mobile)
- [ ] Icons from lucide-react

#### 2.2 Requirements Card
**File:** `frontend/src/features/projects/components/overview/RequirementsCard.tsx`
- [ ] Categorized display (Business, Functional, NFR, Other)
- [ ] Expandable/collapsible groups
- [ ] Show ambiguity badges
- [ ] Source citations as chips
- [ ] Count per category

#### 2.3 Architecture Coverage Card
**File:** `frontend/src/features/projects/components/overview/ArchitectureCoverageCard.tsx`
- [ ] Display mindMapCoverage data
- [ ] Progress rings for each topic
- [ ] Color coding: complete (green), partial (amber), missing (gray)
- [ ] Click to expand details

#### 2.4 WAF Assessment Card
**File:** `frontend/src/features/projects/components/overview/WafAssessmentCard.tsx`
- [ ] 5 pillars: Reliability, Security, Cost, Operational Excellence, Performance
- [ ] Progress rings using recharts RadialBarChart
- [ ] Display findings count per pillar
- [ ] Color-coded severity (critical: red, high: orange, medium: yellow, low: blue)

#### 2.5 Quick Actions Panel
**File:** `frontend/src/features/projects/components/overview/QuickActions.tsx`
- [ ] "Analyze Documents" button → navigate to Workspace
- [ ] "Generate Candidate" button → opens chat with pre-filled prompt
- [ ] "Create ADR" button → opens chat with ADR template
- [ ] "Export Proposal" button → triggers proposal generation
- [ ] "View Diagrams" button → navigate to Deliverables

#### 2.6 Activity Timeline
**File:** `frontend/src/features/projects/components/overview/ActivityTimeline.tsx`
- [ ] Display iterationEvents sorted by timestamp
- [ ] Visual timeline with dots and connecting lines
- [ ] Event types with icons (analysis, candidate, ADR, finding, cost, etc.)
- [ ] Citations displayed as expandable chips
- [ ] Limit to last 10 events, "View All" link

---

### 📝 Phase 3: Workspace Components

#### 3.1 Chat Panel
**File:** `frontend/src/features/projects/components/workspace/ChatPanel.tsx`
- [ ] Message bubbles with avatars (user vs assistant)
- [ ] Code blocks with syntax highlighting (react-syntax-highlighter)
- [ ] Citation chips that open modal on click
- [ ] Loading animation while agent responds
- [ ] Suggested follow-up questions
- [ ] Input with send button and keyboard shortcut (Cmd+Enter)

#### 3.2 Context Sidebar
**File:** `frontend/src/features/projects/components/workspace/ContextSidebar.tsx`
- [ ] Collapsible sidebar (can be toggled)
- [ ] Tabs: Requirements, Assumptions, Questions, Documents
- [ ] Requirements tab: grouped by category with counts
- [ ] Assumptions tab: list with sources
- [ ] Questions tab: sorted by priority with status badges
- [ ] Documents tab: uploaded files with preview icons

#### 3.3 Document Upload Zone
**File:** `frontend/src/features/projects/components/workspace/DocumentUpload.tsx`
- [ ] Drag-and-drop area (using native HTML5 drag-drop)
- [ ] File list with remove button
- [ ] Upload progress indicator
- [ ] Support for multiple file types (PDF, DOCX, TXT, MD)
- [ ] Integrated into Chat Panel header

---

### 📐 Phase 4: Deliverables Components

#### 4.1 Diagram Gallery
**File:** `frontend/src/features/projects/components/deliverables/DiagramGallery.tsx`
- [ ] Grid layout with diagram cards
- [ ] Filter buttons: All, C4 Context, C4 Container, Functional
- [ ] Each card shows: thumbnail (mermaid render), title, type badge, timestamp
- [ ] Click to open full-screen modal with zoom controls
- [ ] Export buttons (SVG, PNG)
- [ ] Empty state: "No diagrams yet. Generate one in Workspace."

#### 4.2 ADR Library
**File:** `frontend/src/features/projects/components/deliverables/AdrLibrary.tsx`
- [ ] Toggle view: Table / Card grid
- [ ] Search bar (filters by title, context, decision)
- [ ] Filter by status: All, Draft, Accepted, Deprecated, Superseded
- [ ] Sort by: Date (newest/oldest), Status, Title
- [ ] Table columns: Title, Status, Created, Related (count)
- [ ] Card view: compact cards with expand button
- [ ] Click to open full-screen reader mode
- [ ] Reader mode: full ADR content with related items sidebar
- [ ] Show related requirements, diagrams, WAF evidence as chips

#### 4.3 IaC Viewer
**File:** `frontend/src/features/projects/components/deliverables/IacViewer.tsx`
- [ ] List of IaC artifacts (sorted by date)
- [ ] Each artifact: file tabs (Bicep, Terraform, parameters, etc.)
- [ ] Monaco editor or react-syntax-highlighter for code display
- [ ] Read-only mode with copy button
- [ ] Download individual file button
- [ ] "Download All as ZIP" button
- [ ] Validation results displayed with badges (passed, failed, warnings)

#### 4.4 Cost Breakdown
**File:** `frontend/src/features/projects/components/deliverables/CostBreakdown.tsx`
- [ ] List of cost estimates (sorted by date)
- [ ] Each estimate card shows:
  - Total monthly cost (large, prominent)
  - Currency code
  - Timestamp
  - Variance % if baseline exists
- [ ] Pie chart using recharts (services by cost)
- [ ] Line items table (expandable)
- [ ] Pricing gaps section with warning badges
- [ ] Export to CSV button

---

### 📄 Phase 5: Page Components

#### 5.1 Project Overview Page
**File:** `frontend/src/features/projects/pages/ProjectOverviewPage.tsx`
- [ ] Import all overview components
- [ ] Grid layout: 
  - Row 1: HeroStats (4 columns)
  - Row 2: RequirementsCard (col-span-2), ArchitectureCoverageCard (col-span-1), WafAssessmentCard (col-span-1)
  - Row 3: ActivityTimeline (col-span-2), QuickActions (col-span-2)
- [ ] Responsive: stack on mobile
- [ ] Loading state: show skeletons
- [ ] Empty state: "Start by uploading documents in Workspace"

#### 5.2 Project Workspace Page
**File:** `frontend/src/features/projects/pages/ProjectWorkspacePage.tsx`
- [ ] Split layout: ChatPanel (70%) | ContextSidebar (30%)
- [ ] Sidebar toggle button
- [ ] When sidebar closed, chat expands to 100%
- [ ] Responsive: sidebar becomes overlay on mobile

#### 5.3 Project Deliverables Page
**File:** `frontend/src/features/projects/pages/ProjectDeliverablesPage.tsx`
- [ ] Tabbed layout: Diagrams, ADRs, IaC, Costs
- [ ] Each tab mounts its respective component
- [ ] Tabs persist selection in URL query param

---

### 🔧 Phase 6: Routing & Integration

#### 6.1 Update Tab Definitions
**Files to modify:**
- `frontend/src/features/projects/tabs/definitions/overview.tsx` (NEW)
- `frontend/src/features/projects/tabs/definitions/workspace.tsx` (NEW)
- `frontend/src/features/projects/tabs/definitions/deliverables.tsx` (NEW)
- Delete: `aaa.tsx`, `chat.tsx`, `state.tsx`, `documents.tsx`, `diagrams.tsx`, `proposal.tsx`

#### 6.2 Update Tab Registry
**File:** `frontend/src/features/projects/tabs/index.ts`
- [ ] Import only new 3 tabs
- [ ] Register in order: overview, workspace, deliverables

#### 6.3 Update Routes
**File:** `frontend/src/app/routes.tsx`
- [ ] Update project detail routes to use new tabs
- [ ] Ensure default tab is "overview"

#### 6.4 Update ProjectDetailPage
**File:** `frontend/src/features/projects/pages/ProjectDetailPage.tsx`
- [ ] Update tab navigation to show only 3 tabs
- [ ] Update default active tab to "overview"

---

### 📊 Phase 7: Data Visualization

#### 7.1 Cost Pie Chart
**File:** `frontend/src/features/projects/components/deliverables/charts/CostPieChart.tsx`
- [ ] Use recharts PieChart
- [ ] Show top 5 services by cost
- [ ] "Others" category for remaining
- [ ] Legend with percentages
- [ ] Tooltip on hover

#### 7.2 WAF Radar Chart
**File:** `frontend/src/features/projects/components/overview/charts/WafRadarChart.tsx`
- [ ] Use recharts RadarChart
- [ ] 5 axes (one per pillar)
- [ ] Score based on findings (inverse: fewer findings = higher score)
- [ ] Color fill based on overall health

#### 7.3 Coverage Progress Rings
**File:** `frontend/src/features/projects/components/overview/charts/CoverageProgress.tsx`
- [ ] Use recharts RadialBarChart for circular progress
- [ ] One ring per mind map topic
- [ ] Color: complete (green), partial (yellow), missing (red)
- [ ] Percentage in center

#### 7.4 Activity Timeline Visualization
**File:** `frontend/src/features/projects/components/overview/charts/TimelineChart.tsx`
- [ ] Vertical timeline with connecting line
- [ ] Dots for each event (color by type)
- [ ] Icon inside dot
- [ ] Date labels
- [ ] Event description on right

---

### ⚡ Phase 8: Advanced Features

#### 8.1 Search & Filter
- [ ] ADR Library: client-side search (title, context, decision text)
- [ ] ADR Library: filter by status dropdown
- [ ] Diagram Gallery: filter by type chips
- [ ] Document list: search by filename

#### 8.2 Keyboard Shortcuts
- [ ] Cmd+K: Command palette (open quick action menu)
- [ ] Cmd+/: Toggle context sidebar
- [ ] Cmd+Enter: Send chat message
- [ ] Esc: Close modals/overlays

#### 8.3 Command Palette
**File:** `frontend/src/features/projects/components/common/CommandPalette.tsx`
- [ ] Modal overlay with search input
- [ ] Quick actions: Navigate to tabs, Trigger analysis, Generate artifacts
- [ ] Keyboard navigation (arrow keys)
- [ ] Fuzzy search

#### 8.4 Drag-and-Drop Upload
**File:** `frontend/src/features/projects/components/workspace/DocumentUpload.tsx`
- [ ] HTML5 drag-drop API
- [ ] Visual feedback on drag-over
- [ ] Support multiple files
- [ ] Auto-upload on drop

#### 8.5 Inline Editing
- [ ] Requirements: click to edit text
- [ ] Assumptions: click to edit
- [ ] Save on blur or Enter key
- [ ] API call to update project state

---

### 🎨 Phase 9: Polish & Testing

#### 9.1 Loading States
- [ ] Skeleton screens for all major components
- [ ] Loading spinners for actions
- [ ] Progress bars for uploads
- [ ] Shimmer effect on skeletons

#### 9.2 Empty States
- [ ] Overview: "Upload documents to get started"
- [ ] Diagrams: "No diagrams yet. Generate one in Workspace."
- [ ] ADRs: "No ADRs yet. Create one via Chat."
- [ ] Costs: "No estimates yet. Request one from the agent."
- [ ] Each with icon + CTA button

#### 9.3 Error Boundaries
**File:** `frontend/src/components/common/ErrorBoundary.tsx`
- [ ] Catch React errors in component tree
- [ ] Display friendly error message
- [ ] "Report Issue" button
- [ ] Reset boundary button

#### 9.4 Toast Notifications
- [ ] Success: "Document uploaded", "ADR created"
- [ ] Error: "Upload failed", "Analysis error"
- [ ] Info: "Generating proposal..."
- [ ] Position: top-right
- [ ] Auto-dismiss after 5s

#### 9.5 Testing Workflows
- [ ] Test complete user flow: Upload → Analyze → Chat → Generate ADR → View Deliverables
- [ ] Test all empty states
- [ ] Test error scenarios
- [ ] Test responsive layouts (desktop, tablet, mobile - though mobile not priority)
- [ ] Test keyboard shortcuts
- [ ] Test loading states

---

## Design System Reference

### Color Palette
```
Primary:   Azure Blue (#0078D4, text-blue-600)
Success:   Green (#107C10, text-green-600)
Warning:   Amber (#F7630C, text-amber-600)
Error:     Red (#D13438, text-red-600)
Info:      Cyan (text-cyan-600)
Neutral:   Tailwind gray-50 to gray-900
```

### Typography Scale
```
Hero:      text-3xl font-bold
Section:   text-xl font-semibold
Subsection: text-lg font-semibold
Body:      text-base
Small:     text-sm
Caption:   text-xs text-gray-600
```

### Component Patterns
- **Cards:** `shadow-sm`, `border-gray-200`, `rounded-lg`, hover effects
- **Badges:** Rounded pills, semantic colors
- **Icons:** lucide-react, 24px default
- **Spacing:** Consistent padding (px-6 py-4 for cards)
- **Transitions:** `transition-all duration-200` for smooth interactions

### Icons (lucide-react)
- Requirements: CheckSquare
- ADRs: FileText
- Findings: AlertTriangle
- Cost: DollarSign
- Diagrams: Network
- Documents: File
- Upload: Upload
- Download: Download
- Chat: MessageSquare
- Search: Search
- Filter: Filter
- Settings: Settings

---

## Dependencies Added

```json
{
  "lucide-react": "^latest",
  "recharts": "^latest",
  "react-syntax-highlighter": "^latest",
  "react-markdown": "^latest",
  "@types/react-syntax-highlighter": "^latest"
}
```

---

## File Structure

```
frontend/src/
├── components/
│   └── common/
│       ├── Card.tsx ✅
│       ├── Badge.tsx ✅
│       ├── EmptyState.tsx ✅
│       ├── StatCard.tsx ✅
│       ├── LoadingSkeleton.tsx ✅
│       ├── ErrorBoundary.tsx ⏳
│       └── index.ts ✅
├── features/
│   └── projects/
│       ├── components/
│       │   ├── overview/
│       │   │   ├── HeroStats.tsx ⏳
│       │   │   ├── RequirementsCard.tsx ⏳
│       │   │   ├── ArchitectureCoverageCard.tsx ⏳
│       │   │   ├── WafAssessmentCard.tsx ⏳
│       │   │   ├── QuickActions.tsx ⏳
│       │   │   ├── ActivityTimeline.tsx ⏳
│       │   │   └── charts/
│       │   │       ├── WafRadarChart.tsx ⏳
│       │   │       ├── CoverageProgress.tsx ⏳
│       │   │       └── TimelineChart.tsx ⏳
│       │   ├── workspace/
│       │   │   ├── ChatPanel.tsx ⏳
│       │   │   ├── ContextSidebar.tsx ⏳
│       │   │   └── DocumentUpload.tsx ⏳
│       │   ├── deliverables/
│       │   │   ├── DiagramGallery.tsx ⏳
│       │   │   ├── AdrLibrary.tsx ⏳
│       │   │   ├── IacViewer.tsx ⏳
│       │   │   ├── CostBreakdown.tsx ⏳
│       │   │   └── charts/
│       │   │       └── CostPieChart.tsx ⏳
│       │   └── common/
│       │       └── CommandPalette.tsx ⏳
│       ├── pages/
│       │   ├── ProjectOverviewPage.tsx ⏳
│       │   ├── ProjectWorkspacePage.tsx ⏳
│       │   └── ProjectDeliverablesPage.tsx ⏳
│       └── tabs/
│           └── definitions/
│               ├── overview.tsx ⏳
│               ├── workspace.tsx ⏳
│               └── deliverables.tsx ⏳
```

Legend: ✅ Complete | ⏳ Pending | ❌ Blocked

---

## Next Steps

1. Continue with Phase 2: Build Overview Dashboard components
2. Create HeroStats component
3. Create RequirementsCard component
4. Continue through phases sequentially

---

## Notes & Decisions

- **Design inspiration:** Notion-style clean interface with cards and subtle shadows
- **Performance:** Use virtualization for long lists (react-window if needed)
- **Diagram rendering:** Mermaid diagrams rendered on-demand, with caching
- **Mobile:** Not priority for now, but keep structure responsive for future
- **Accessibility:** Ensure keyboard navigation, ARIA labels, screen reader support
- **State management:** Use existing useProjectContext, no additional state lib needed
