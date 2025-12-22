# Glosses4Learning CMS - General CRUD

General-purpose CRUD interface for managing glosses.

## Setup

1. Add `glosses4learning-core` as submodule:
   ```bash
   git submodule add ../glosses4learning-core packages/core
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Link data directory (share with sbll-cms):
   ```bash
   ln -s ../sbll-cms/data ./data
   ```

4. Run dev:
   ```bash
   npm run dev
   ```

## Structure

- **Gloss Browser** - Browse and search all glosses
- **Gloss Editor** - Full CRUD operations
- **Relationship Graph** - Visualize connections
- **Bulk Operations** - Import/export/batch edit

## No Situation Logic

This CMS has NO situation-specific features:
- No goal types
- No RED/YELLOW states
- No situation export
- Pure gloss management only
