# Unified UX Implementation Checklist - Option 3

## Goal
Create a chat-first interface with collapsible left (context) and right (deliverables) sidebars, eliminating tab navigation.

## Phase 1: Investigation & Data Wiring ✅ COMPLETE

### ADR Display Issue Investigation ✅
- [x] Check projectState structure for ADRs - Found in AAAProjectState model
- [x] Verify useProjectState hook calls ADR endpoint - Uses stateApi.fetch()
- [x] Check backend endpoint - `/projects/{project_id}/state` calls read_project_state()
- [x] Verify backend returns ADRs - AAAProjectState includes adrs: list[AdrArtifact]
- [x] Fix TypeScript types - Added complete ProjectState interface with all AAA artifacts
- [x] Remove `(state as any)` casts - Now use properly typed projectState
- [x] Document actual ADR data structure - See AdrArtifact in api.ts

### TypeScript Type System Fixes ✅
- [x] Added AdrArtifact, FindingArtifact, CostEstimate to api.ts
- [x] Added WafChecklist, IacArtifact, TraceabilityLink interfaces
- [x] Updated ProjectState to include all AAA artifacts
- [x] Made all component prop interfaces accept readonly arrays
- [x] Fixed component-local type definitions to use readonly
- [x] All TypeScript errors resolved

### Verified Data Sources ✅
- [x] ADRs: projectState.adrs (readonly AdrArtifact[])
- [x] Diagrams: projectState.diagrams (readonly Record<string, any>[])
- [x] Cost estimates: projectState.costEstimates (readonly CostEstimate[])
- [x] Architecture coverage: projectState.mindMapCoverage (Record<string, any>)
- [x] WAF assessment: projectState.findings (readonly FindingArtifact[])
- [x] Requirements: projectState.requirements
- [x] Assumptions: projectState.assumptions
- [x] Questions: projectState.clarificationQuestions
- [x] Iteration events: projectState.iterationEvents

## Phase 2: Component Creation

### 2.1 Quick Actions Bar Component
- [ ] Create `QuickActionsBar.tsx`
- [ ] Add project name display
- [ ] Add action buttons (Upload, Generate, Create ADR, Export)
- [ ] Make it sticky at top
- [ ] Add keyboard shortcut hints
- [ ] Style with Tailwind (consistent with design system)
- [ ] Make responsive (collapse to menu icon on mobile)

### 2.2 Right Deliverables Panel Component
- [ ] Create `RightDeliverablesPanel.tsx`
- [ ] Add toggle button to collapse/expand
- [ ] Add mini stats section (4 key metrics)
- [ ] Add diagrams section (compact thumbnails)
- [ ] Add ADRs section (list with status badges)
- [ ] Add cost summary section (mini pie chart + total)
- [ ] Make each section independently collapsible
- [ ] Add scroll behavior
- [ ] Persist open/closed state in localStorage

### 2.3 Left Context Panel Component
- [ ] Create `LeftContextPanel.tsx`
- [ ] Reuse ContextSidebar tab logic
- [ ] Add toggle button to collapse/expand
- [ ] Style for left-side docking
- [ ] Keep 4 tabs: Requirements, Assumptions, Questions, Documents
- [ ] Add proper scroll handling
- [ ] Persist open/closed state in localStorage

### 2.4 Center Chat Area Component
- [ ] Create `CenterChatArea.tsx`
- [ ] Integrate existing ChatPanel
- [ ] Add collapsible document upload section
- [ ] Adjust padding for tighter layout
- [ ] Ensure proper height calculation
- [ ] Keep all existing chat functionality

### 2.5 Unified Project Page Component
- [ ] Create `UnifiedProjectPage.tsx`
- [ ] Build 3-column flexbox layout
- [ ] Wire up all three panels + quick actions bar
- [ ] Handle sidebar collapse states
- [ ] Add keyboard shortcuts (Cmd+[ left, Cmd+] right)
- [ ] Make responsive (stack on tablet/mobile)
- [ ] Add ErrorBoundary wrapper

## Phase 3: Component Integration

### 3.1 Data Flow Wiring
- [ ] Pass messages to center chat area
- [ ] Pass requirements/assumptions/questions to left panel
- [ ] Pass ADRs to right panel
- [ ] Pass diagrams to right panel
- [ ] Pass cost estimates to right panel
- [ ] Pass project stats to right panel
- [ ] Verify all data updates reactively

### 3.2 Action Handlers
- [ ] Wire up document upload handler
- [ ] Wire up chat message handler
- [ ] Wire up generate diagram action
- [ ] Wire up create ADR action
- [ ] Wire up export actions
- [ ] Wire up navigation actions

## Phase 4: Routing & Navigation Updates

### 4.1 Remove Tab System
- [ ] Comment out old tab definitions (don't delete yet)
- [ ] Remove tab registration from tabs/index.ts
- [ ] Remove TabNavigation component from ProjectDetailPage
- [ ] Keep old components temporarily for reference

### 4.2 Update Routes
- [ ] Update routes.tsx to point to UnifiedProjectPage
- [ ] Remove Navigate redirect to tabs
- [ ] Ensure direct project URL works
- [ ] Test browser back/forward buttons

### 4.3 Clean Up Command Palette
- [ ] Remove tab navigation commands
- [ ] Update navigation to use sidebar toggles
- [ ] Add new quick action commands

## Phase 5: Visual Polish & Responsive Design

### 5.1 Layout Polish
- [ ] Verify proper spacing between panels
- [ ] Add subtle dividers/borders
- [ ] Ensure consistent card styling
- [ ] Add smooth transitions for collapse/expand
- [ ] Test with different viewport sizes

### 5.2 Responsive Behavior
- [ ] Desktop (1920px+): Show all 3 columns
- [ ] Laptop (1024-1919px): Show all, narrower sidebars
- [ ] Tablet (768-1023px): Hide right panel by default
- [ ] Mobile (<768px): Hide both panels, show toggle buttons

### 5.3 Accessibility
- [ ] Add ARIA labels to toggle buttons
- [ ] Ensure keyboard navigation works
- [ ] Test with screen reader
- [ ] Add focus indicators
- [ ] Ensure color contrast meets WCAG AA

## Phase 6: Testing & Validation

### 6.1 Functional Testing
- [ ] Chat sends and receives messages correctly
- [ ] Document upload works
- [ ] Sidebar toggles persist
- [ ] All data displays correctly
- [ ] Empty states show when appropriate
- [ ] Loading states display properly

### 6.2 Data Display Testing
- [ ] Requirements display in left panel
- [ ] Assumptions display in left panel
- [ ] Questions display in left panel
- [ ] ADRs display in right panel ⚠️
- [ ] Diagrams display in right panel
- [ ] Costs display in right panel
- [ ] Stats display in right panel

### 6.3 Interaction Testing
- [ ] Sidebar collapse/expand smooth
- [ ] Quick actions trigger correct behavior
- [ ] Keyboard shortcuts work
- [ ] Command palette still functional
- [ ] Scroll behavior correct in all panels

### 6.4 Performance Testing
- [ ] Large chat history doesn't lag
- [ ] Many diagrams render efficiently
- [ ] Sidebar toggles are instant
- [ ] No memory leaks with long sessions

## Phase 7: Documentation & Cleanup

### 7.1 Code Cleanup
- [ ] Remove unused tab components (after testing)
- [ ] Remove old Overview/Workspace/Deliverables pages
- [ ] Update component exports
- [ ] Remove dead code

### 7.2 Documentation Updates
- [ ] Update FRONTEND_REFERENCE.md
- [ ] Document new component structure
- [ ] Add screenshots of new layout
- [ ] Document keyboard shortcuts
- [ ] Update any user guides

## Phase 8: Final Review

### 8.1 Code Quality
- [ ] No TypeScript errors
- [ ] No console warnings
- [ ] No Tailwind warnings
- [ ] Proper error handling
- [ ] Clean code structure

### 8.2 User Experience
- [ ] Intuitive to use
- [ ] Fast and responsive
- [ ] Clear visual hierarchy
- [ ] Easy to find information
- [ ] Quick actions accessible

### 8.3 Ready for Production
- [ ] All tests passing
- [ ] No known bugs
- [ ] Performance acceptable
- [ ] Documentation complete
- [ ] Team review completed

---

## Current Status

**Phase**: 1 - Investigation
**Next Action**: Investigate ADR data structure and display issue
**Blocker**: None
**Notes**: Starting implementation now

## Estimated Timeline

- Phase 1: 1 hour
- Phase 2: 4 hours
- Phase 3: 2 hours
- Phase 4: 1 hour
- Phase 5: 2 hours
- Phase 6: 2 hours
- Phase 7: 1 hour
- Phase 8: 1 hour

**Total: ~14 hours** (can be split across multiple sessions)
