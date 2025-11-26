# Components Folder Structure

## New Organization

```
frontend/src/components/
├── common/                    # Reusable UI components
│   ├── index.ts              # Barrel export
│   ├── Navigation.tsx        # Top-level navigation bar
│   └── TabNavigation.tsx     # Generic tab navigation
│
├── kb/                       # Knowledge Base feature components
│   ├── index.ts              # Barrel export
│   ├── KBWorkspace.tsx       # Main KB workspace container
│   ├── KBHeader.tsx          # KB page header
│   ├── KBLoadingScreen.tsx   # Loading state
│   ├── KBQueryForm.tsx       # Query input form
│   ├── KBQueryResults.tsx    # Results display
│   └── KBStatusNotReady.tsx  # Error/warning state
│
└── projects/                 # Project workspace components
    ├── index.ts              # Barrel export
    ├── ProjectWorkspace.tsx  # Main workspace container
    ├── ProjectList.tsx       # Project sidebar
    ├── ChatPanel.tsx         # Chat interface
    ├── DocumentsPanel.tsx    # Document management
    ├── StatePanel.tsx        # Project state view
    └── ProposalPanel.tsx     # Architecture proposal
```

## Hooks Structure

```
frontend/src/hooks/
├── useKBWorkspace.ts         # KB workspace orchestration hook
├── useKBHealth.ts            # KB health checking
├── useKBQuery.ts             # KB query logic
├── useProjectWorkspace.ts    # Project workspace orchestration hook
├── useProjects.ts            # Project management
├── useProjectState.ts        # Project state management
├── useChat.ts                # Chat functionality
└── useProposal.ts            # Proposal generation
```

## Benefits

### 🎯 **Clear Separation by Feature**
- `common/` - Generic, reusable components
- `kb/` - Knowledge Base query feature
- `projects/` - Project management feature

### 📦 **Barrel Exports**
Each folder has an `index.ts` for cleaner imports:

**Before:**
```typescript
import { Navigation } from './components/common/Navigation'
import { ProjectWorkspace } from './components/projects/ProjectWorkspace'
import { KBHeader } from './components/kb/KBHeader'
```

**After:**
```typescript
import { Navigation } from './components/common'
import { ProjectWorkspace } from './components/projects'
import { KBHeader } from './components/kb'
```

### 🔍 **Easy to Navigate**
- Related components grouped together
- Clear feature boundaries
- Intuitive file locations

### 🧩 **Scalability**
- Add new features as new folders
- Common components remain separate
- Easy to move to separate packages later

## Usage Examples

### App.tsx
```typescript
import { Navigation } from './components/common'
import { ProjectWorkspace } from './components/projects'
import { KBWorkspace } from './components/kb'
```

### ProjectWorkspace.tsx
```typescript
import { ProjectList, ChatPanel, StatePanel } from '.'
import { TabNavigation } from '../common'
import { useProjectWorkspace } from '../../hooks/useProjectWorkspace'
```

### KBWorkspace.tsx
```typescript
import { KBHeader, KBQueryForm, KBQueryResults } from '.'
import { useKBWorkspace } from '../../hooks/useKBWorkspace'
```

## Guidelines

1. **common/** - Only components used by multiple features
2. **Feature folders** - Components specific to that feature
3. **index.ts** - Always export public components
4. **Naming** - Keep component names descriptive and prefixed when appropriate (e.g., KB*, Project*)
