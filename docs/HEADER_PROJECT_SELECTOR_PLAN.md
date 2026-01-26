# Header Project Selector - Implementation Plan

## Overview
Implement a sticky header with an integrated project dropdown selector that allows users to switch projects from any page without scrolling or navigation. Includes project deletion capability.

## Design Requirements
- **Always Visible**: Sticky header positioned at top of viewport
- **Small & Compact**: Minimal height to maximize content area
- **Quick Access**: Dropdown accessible with one click
- **Project Management**: View all projects, switch instantly, delete projects
- **No Backend Yet**: UI/UX implementation only, mock backend calls

---

## Task Breakdown

### Phase 1: Header Component Structure

#### Task 1.1: Create ProjectSelectorDropdown Component
**File**: `frontend/src/components/common/ProjectSelectorDropdown.tsx`
**Objective**: Build the dropdown menu component
**Details**:
- Create dropdown with trigger button showing current project
- Display project name with icon
- Down chevron indicator
- Implement open/close state management
- Click outside to close functionality
- Keyboard navigation (Arrow keys, Enter, Escape)

**Acceptance Criteria**:
- Dropdown opens on click
- Closes when clicking outside
- Accessible via keyboard
- Smooth animations (fade in/out)

---

#### Task 1.2: Build Project List UI
**File**: `frontend/src/components/common/ProjectSelectorDropdown.tsx` (continued)
**Objective**: Design the dropdown content
**Details**:
- Search input at top (filter projects by name)
- Scrollable project list (max height 400px)
- Each project item shows:
  - Project icon/avatar
  - Project name
  - Last updated date (small text)
  - Active indicator (checkmark or highlight)
  - Delete button (trash icon, shows on hover)
- "Create New Project" button at bottom
- Empty state when no projects found
- Loading state skeleton

**Acceptance Criteria**:
- Search filters projects in real-time
- Current project is highlighted
- Hover states work correctly
- Delete button appears on row hover
- Smooth scrolling

---

#### Task 1.3: Integrate with Layout Header
**File**: `frontend/src/app/Layout.tsx`
**Objective**: Add sticky header with project selector
**Details**:
- Add sticky header with `position: sticky, top: 0, z-index: 50`
- Header layout:
  - Left: Logo/App name
  - Center: ProjectSelectorDropdown
  - Right: Navigation links (KB, Ingestion, Agent Chat)
- Small height: 56px (h-14)
- Background: white with subtle shadow
- Ensure header doesn't overlap with page content

**Acceptance Criteria**:
- Header stays at top when scrolling
- Doesn't overlap page content
- Responsive on different screen sizes
- Smooth shadow appearance

---

### Phase 2: State Management & Logic

#### Task 2.1: Create useProjectSelector Hook
**File**: `frontend/src/hooks/useProjectSelector.ts`
**Objective**: Manage project selection state and operations
**Details**:
- Fetch all projects from API (or mock)
- Track currently selected project
- Handle project switching (update URL, context)
- Search/filter logic
- Delete project handler (with confirmation)
- Loading and error states

**API Methods** (mocked for now):
```typescript
- fetchProjects(): Promise<Project[]>
- switchProject(projectId: string): Promise<void>
- deleteProject(projectId: string): Promise<void>
```

**Acceptance Criteria**:
- Projects load on mount
- Switching updates URL to `/projects/:projectId`
- Delete shows confirmation modal
- Handles loading/error states gracefully

---

#### Task 2.2: Add Project Context Updates
**File**: `frontend/src/features/projects/context/ProjectContext.tsx`
**Objective**: Ensure project context updates when switching
**Details**:
- Listen to project changes from selector
- Update `selectedProject` state
- Fetch new project data when switched
- Clear old project data before loading new
- Update route without full page reload

**Acceptance Criteria**:
- Context updates immediately on switch
- No stale data from previous project
- Smooth transition without flicker

---

### Phase 3: UI Polish & Interactions

#### Task 3.1: Implement Delete Confirmation Modal
**File**: `frontend/src/components/common/DeleteProjectModal.tsx`
**Objective**: Safe project deletion with confirmation
**Details**:
- Modal appears when delete button clicked
- Shows project name to confirm
- Warning message about data loss
- Two buttons: "Cancel" (secondary) and "Delete" (danger red)
- Keyboard support (Enter to delete, Escape to cancel)
- Disable delete button while processing

**Acceptance Criteria**:
- Modal appears centered and overlays page
- User must explicitly confirm deletion
- Shows loading state during deletion
- Closes on successful deletion
- Shows error if deletion fails

---

#### Task 3.2: Add Loading & Empty States
**Files**: Multiple components
**Objective**: Handle edge cases gracefully
**Details**:

**Loading State**:
- Skeleton loader in dropdown while fetching projects
- Button shows spinner during operations

**Empty State**:
- "No projects yet" message with illustration
- "Create your first project" CTA button
- Search with no results: "No projects match your search"

**Error State**:
- Toast notification for errors
- Retry button if project fetch fails

**Acceptance Criteria**:
- All states have clear visual feedback
- User is never left confused
- Errors are actionable

---

#### Task 3.3: Responsive Design
**Files**: All component files
**Objective**: Works on mobile, tablet, desktop
**Details**:
- Mobile: Dropdown takes full width, close button in corner
- Tablet: Standard dropdown, slightly narrower
- Desktop: Full-featured dropdown
- Touch-friendly tap targets (min 44px)
- Test on viewport widths: 375px, 768px, 1024px, 1440px

**Acceptance Criteria**:
- Dropdown doesn't overflow screen on mobile
- Touch targets easy to tap
- Readable on all screen sizes

---

### Phase 4: Integration & Testing

#### Task 4.1: Wire Up Navigation Links
**File**: `frontend/src/app/Layout.tsx`
**Objective**: Ensure header navigation works correctly
**Details**:
- Update "Projects" link behavior (open dropdown or navigate)
- KB, Ingestion, Agent Chat links work
- Active route highlighting
- Preserve selected project when navigating to other pages

**Acceptance Criteria**:
- All navigation links functional
- Current route highlighted
- Project context persists across pages

---

#### Task 4.2: Add Keyboard Shortcuts
**File**: `frontend/src/components/common/ProjectSelectorDropdown.tsx`
**Objective**: Power user shortcuts
**Details**:
- `Cmd/Ctrl + P`: Open project selector
- `Arrow Up/Down`: Navigate project list
- `Enter`: Select highlighted project
- `Escape`: Close dropdown
- `/` or `Cmd+K`: Focus search input

**Acceptance Criteria**:
- Shortcuts work globally (except when typing)
- Visual hint for shortcuts in UI
- No conflicts with browser shortcuts

---

#### Task 4.3: Handle Edge Cases
**Files**: Multiple components
**Objective**: Robust error handling
**Details**:

**No Project Selected**:
- Show "Select a Project" in header
- Dropdown defaults to "All Projects" view

**Project Deleted While Viewing**:
- Redirect to projects list page
- Show toast: "Project was deleted"

**Network Failure**:
- Retry mechanism
- Cached project list as fallback

**Very Long Project Names**:
- Truncate with ellipsis
- Full name in tooltip on hover

**Acceptance Criteria**:
- App doesn't crash on edge cases
- User always has clear feedback
- Graceful degradation

---

### Phase 5: Visual Polish

#### Task 5.1: Add Animations
**Files**: Component files
**Objective**: Smooth, delightful interactions
**Details**:
- Dropdown: Fade + slide down (200ms ease-out)
- Project hover: Subtle background color shift
- Delete button: Scale in on hover
- Active project: Pulse or glow effect
- Search: Debounced input (300ms)

**Acceptance Criteria**:
- Animations feel smooth, not janky
- No animation flicker
- Reduced motion respected (prefers-reduced-motion)

---

#### Task 5.2: Finalize Styling
**Files**: All components
**Objective**: Match design system
**Details**:
- Colors: Use existing Tailwind theme
- Typography: Consistent font sizes (text-sm, text-base)
- Spacing: 4px grid (gap-1, gap-2, gap-4)
- Shadows: Subtle elevation for dropdown
- Icons: lucide-react, 16px or 20px
- Focus states: Blue ring (ring-2 ring-blue-500)

**Design Tokens**:
```
Header: bg-white, border-b, shadow-sm
Dropdown: bg-white, rounded-lg, shadow-lg
Project Item: hover:bg-gray-50, active:bg-blue-50
Delete Button: text-red-600, hover:bg-red-50
```

**Acceptance Criteria**:
- Consistent with app design language
- Accessible contrast ratios (WCAG AA)
- Clear visual hierarchy

---

## Implementation Order

1. **Start Here**: Task 1.1 → 1.2 → 1.3 (Build UI structure)
2. **Then**: Task 2.1 → 2.2 (Add logic and state)
3. **Next**: Task 3.1 → 3.2 → 3.3 (Polish interactions)
4. **Finally**: Task 4.1 → 4.2 → 4.3 → 5.1 → 5.2 (Integration & polish)

## Testing Checklist

After implementation, verify:
- [ ] Dropdown opens/closes correctly
- [ ] Search filters projects
- [ ] Switching projects updates URL and context
- [ ] Delete shows confirmation modal
- [ ] Keyboard shortcuts work
- [ ] Responsive on mobile/tablet/desktop
- [ ] No console errors or warnings
- [ ] Accessible (keyboard navigation, screen readers)
- [ ] Animations smooth (60fps)
- [ ] Edge cases handled (no projects, network errors, etc.)

## Future Backend Integration (Not in Scope)

When ready to connect backend:
1. Replace mock API calls in `useProjectSelector` with real endpoints
2. Update `projectService.ts` with new methods:
   - `GET /api/projects` - List all projects
   - `DELETE /api/projects/:id` - Delete project
3. Add optimistic updates for better perceived performance
4. Handle API errors with proper error boundaries

---

## Files to Create/Modify

### New Files:
- `frontend/src/components/common/ProjectSelectorDropdown.tsx`
- `frontend/src/components/common/DeleteProjectModal.tsx`
- `frontend/src/hooks/useProjectSelector.ts`
- `frontend/src/components/common/ConfirmDialog.tsx` (reusable)

### Modified Files:
- `frontend/src/app/Layout.tsx`
- `frontend/src/features/projects/context/ProjectContext.tsx`
- `frontend/src/types/api.ts` (if needed for Project type updates)

---

## Success Metrics

- **User Task Time**: Switch projects in < 3 seconds (vs current ~10s)
- **Clicks Reduced**: 1 click to open dropdown (vs 2 clicks + page load)
- **Discoverability**: Header always visible (vs hidden below fold)
- **Satisfaction**: Smooth animations, no janky scrolling

---

## Notes
- Keep header height minimal (56px) to maximize content area
- Use existing project list API/state where possible
- Mock delete for now, add confirmation to prevent accidents
- Consider adding recent projects section at top of dropdown
- Could add project favorites/pinning in future iteration
