# CODEBUDDY.md

This file provides guidance to CodeBuddy Code when working with code in this repository.

## Project Overview

This is a Vue 3 + Vite frontend application for PDF OCR (Optical Character Recognition) and document processing. The application allows users to upload PDF files, perform OCR using configurable APIs, edit recognized text, and manage notes with AI chat functionality.

## Development Commands

### Build and Development
- `npm run dev` - Start development server with hot reload
- `npm run build` - Build for production
- `npm run preview` - Preview production build locally

### Package Management
The project uses npm for package management (package.json is present alongside pnpm-lock.yaml).

## Architecture

### Tech Stack
- **Frontend Framework**: Vue 3 with Composition API (`<script setup>` syntax)
- **Build Tool**: Vite 5.x
- **Router**: Vue Router 4.x
- **Styling**: Tailwind CSS 3.x with Typography plugin
- **Rich Text Editor**: Quill 2.0 (via @vueup/vue-quill)
- **HTTP Client**: Axios with custom request wrapper
- **PDF Processing**: PDF.js 3.10.111 for client-side PDF rendering and thumbnail generation
- **Icons**: @iconify/vue with Material Design Icons
- **Utilities**: DOMPurify (sanitization), marked (markdown), prismjs (syntax highlighting)

### Project Structure

```
src/
├── api/                 # API layer
│   ├── request.js      # Axios instance with interceptors
│   ├── api.js          # Generic API exports
│   └── file.js         # File-specific API endpoints
├── components/         # Reusable Vue components
│   ├── PreviewSection.vue  # PDF preview with zoom/pan
│   └── PDFPreviewModal.vue # PDF preview modal
├── pages/              # Route components
│   ├── Home.vue        # Landing page with file upload
│   ├── Files.vue       # File management and upload
│   ├── Workspace.vue   # OCR workspace with editor
│   ├── Note.vue        # Note editor with AI chat
│   ├── NoteList.vue    # Note management
│   └── Settings.vue    # OCR configuration management
├── store/              # Local storage state management
│   ├── files.js        # File data (localStorage)
│   └── ocrConfig.js    # OCR API configurations (localStorage)
├── utils/              # Utility functions
│   ├── dbUtils.js      # IndexedDB operations for PDF data
│   └── pdfUtils.js     # PDF.js parsing and thumbnail generation
├── App.vue             # Root component with router-view
├── main.js             # Application entry point
└── router.js           # Route definitions
```

### Key Architectural Patterns

#### API Layer
- Centralized in `src/api/` with a custom Axios wrapper (`request.js`)
- Configured with `withCredentials: true` for cross-origin cookie handling
- Response interceptor automatically unwraps response data (returns `res.data`)
- Request interceptor currently passes through without modification
- Error interceptor redirects to `/w/login` on 401 responses
- The `request()` function signature: `(url, method, data, options = {})`

#### Backend Proxy
Vite dev server proxies `/api/*` requests to `http://127.0.0.1:8000` (configured in vite.config.js:8-17)

#### State Management
Two-tier approach:
1. **localStorage**: Simple key-value storage via `store/files.js` and `store/ocrConfig.js`
2. **IndexedDB**: Complex data storage via `utils/dbUtils.js` for PDF metadata, page content, and thumbnails
   - Database: `OCR_PDF_DB` (version 1)
   - Stores: `pdf_files`, `pdf_pages`, `thumbnails`

#### PDF Processing
Two different PDF processing workflows exist:

**Home.vue Workflow (Client-side):**
1. User uploads PDF → client-side processing via `utils/pdfUtils.js`
2. PDF.js parses the file and generates thumbnails
3. Results saved to IndexedDB via `utils/dbUtils.js`
4. File metadata stored in localStorage via `store/files.js`
5. User navigates to Workspace with blob URL

**Files.vue Workflow (Backend):**
1. User uploads PDF → file sent to backend API (`/api/file/upload`)
2. Backend processes and generates page images
3. Frontend retrieves page data via API (`/api/file/{id}/info`)
4. Images served from backend at `/api/file/{fileId}/image/{page}`

**Note:** The Home.vue workflow uses client-side PDF processing and IndexedDB, while Files.vue uses backend API processing.

#### OCR Integration
- Configured via Settings page (stored in localStorage)
- Active configuration determined by `getActiveConfig()` from `store/ocrConfig.js`
- OCR endpoint called from Workspace: `/api/file/{fileId}/ocr/{page}`

### Page Flow

1. **Home** (`/`) - Landing page with client-side PDF upload and processing
   - Uses `utils/pdfUtils.js` for PDF parsing
   - Saves to IndexedDB via `utils/dbUtils.js`
   - Stores file metadata in localStorage
   - Creates blob URL for Workspace navigation

2. **Files** (`/files`) - File management with backend integration
   - Lists files from backend API
   - Upload files to backend (max 100MB)
   - Drag-and-drop and click-to-upload support
   - Preview, edit, and delete operations
   - Shows file processing status and progress

3. **Workspace** (`/workspace?id={fileId}`) - Main OCR workspace
   - Left: Page thumbnails with navigation (scrollable list)
   - Center: PDF preview with zoom/pan controls
   - Right: Quill editor for editing OCR text
   - Supports both blob URLs (from Home) and backend image URLs (from Files)

4. **Settings** (`/settings`) - OCR API configuration management
   - Manage multiple OCR service configurations
   - Activate/deactivate configurations
   - Configurations stored in localStorage

5. **Note** (`/note?id={noteId}`) - Note editor with AI chat functionality
   - Left: Note list panel
   - Center: Chat interface with AI assistant
   - Right: Work results panel
   - Create, edit, delete notes

6. **NoteList** (`/notes`) - Note management page (basic list view)

### Key Components

#### PreviewSection.vue
- Handles PDF page preview with interactive zoom and pan
- Uses transform-based rendering for performance (CSS transforms)
- Exposes methods: `handleZoomIn()`, `handleZoomOut()`, `resetZoomAndPosition()`
- Interactive controls:
  - Ctrl+wheel: Zoom in/out (0.1x to 5x range)
  - Wheel (no modifier): Scroll vertically
  - Mouse drag: Pan the image
  - Zoom buttons in parent toolbar control this component
- Zoom is centered on mouse position when using Ctrl+wheel
- Boundary constraints prevent image from being dragged completely out of view
- Uses `requestAnimationFrame` for smooth transform updates

#### Workspace.vue
- Main OCR editing interface that works with both Home and Files workflows
- Integrates PreviewSection component
- Quill editor with custom toolbar (headers, formatting, lists, alignment)
- Keyboard shortcuts:
  - Ctrl+S: Save content (only when editor has focus)
  - Arrow Up/Down: Navigate pages when thumbnail list has focus
- Saves selected page position to localStorage (`file_{fileId}_page`)
- Loads previous page position from localStorage on component mount
- OCR operations:
  - Single page OCR via "OCR" button
  - Batch OCR (10 pages) via "批量OCR" button
  - Retry OCR via "重新OCR" button (sets `ocrAgain = true`)
  - Mark page as no OCR needed via "无需OCR" button
- Text utilities:
  - "处理标点" button converts English punctuation to Chinese punctuation
- Features scroll-to-selected-page for thumbnail navigation

### Data Models

#### File (localStorage - from Home.vue workflow)
```javascript
{
  id: string,              // Generated UUID or timestamp
  name: string,            // Original filename
  size: number,            // File size in bytes
  src: string,             // Blob URL (blob:...)
  pages: number,           // Total pages (optional, default 0)
  ocrProgress: number,     // OCR progress percentage (0-100)
  proofProgress: number,   // Proofreading progress percentage (0-100)
  uploadedAt: number       // Upload timestamp
}
```

#### File (from Files.vue backend API)
```javascript
{
  id: string,
  original_filename: string,
  status: 'pending' | 'processing' | 'images_generated' | 'completed' | 'error',
  total_pages: number,
  pages_processed: number,
  created_at: timestamp,
  error_message?: string
}
```

#### Page (in Workspace)
```javascript
{
  index: number,           // Page number (1-based)
  image_url: string,       // Full-size image URL (blob URL or http://127.0.0.1:8000/...)
  thumb_url: string,       // Thumbnail URL
  ocr_text: string,        // Recognized text
  width: number,           // Original width
  height: number           // Original height
}
```

#### OCR Configuration (localStorage)
```javascript
{
  id: string,              // Generated UUID
  name: string,           // Configuration name
  apiUrl: string,         // OCR endpoint URL
  apiKey: string,         // Optional API key
  isActive: boolean       // Whether this config is currently active
}
```

#### Note (from backend API)
```javascript
{
  id: string,
  title: string,
  content: string,
  updated_at: timestamp
}
```

#### Chat Message (Note chat history)
```javascript
{
  role: 'user' | 'assistant',
  content: string,
  timestamp: string (ISO format)
}
```

### Important Configuration

#### Path Aliases
- `@` maps to `/src` (configured in vite.config.js:19-21)

#### Environment Variables
- `VITE_APP_BASE_API` - Base URL for API requests (optional, defaults to proxy)

#### Tailwind CSS
- Content paths: `index.html`, `src/**/*.{vue,js,ts,jsx,tsx}`
- Typography plugin enabled

### API Endpoints

All prefixed with `/api` (proxied to backend at `http://127.0.0.1:8000`):

**Files:**
- `GET /api/file/list` - List all files
- `POST /api/file/upload` - Upload file (multipart/form-data)
- `DELETE /api/file/{id}` - Delete file
- `GET /api/file/{id}/info` - Get file details and pages
- `GET /api/file/{id}/image/{page}` - Get page image
- `POST /api/file/{id}/ocr/{page}` - Perform OCR on page
- `POST /api/file/{id}/noocr/{page}` - Mark page as no OCR needed
- `POST /api/file/content/{id}` - Save page content

**Notes:**
- `GET /api/notes` - List all notes
- `POST /api/notes` - Create note
- `GET /api/notes/{id}` - Get note details
- `PUT /api/notes/{id}` - Update note content
- `DELETE /api/notes/{id}` - Delete note
- `GET /api/notes/{id}/chat` - Get chat history
- `POST /api/notes/{id}/chat` - Send chat message
- `GET /api/notes/{id}/results` - Get work results

## Important Files Reference

### Configuration Files
- `vite.config.js` - Vite configuration with proxy settings and path aliases
- `tailwind.config.js` - Tailwind CSS configuration
- `postcss.config.js` - PostCSS configuration for Tailwind

### Core Application
- `src/main.js` - Application entry point
- `src/App.vue` - Root component with router-view
- `src/router.js` - Vue Router configuration

### API Layer
- `src/api/request.js` - Axios instance with interceptors (withCredentials, 401 handling)
- `src/api/api.js` - Generic API exports
- `src/api/file.js` - File-specific API endpoints

### State Management (localStorage)
- `src/store/files.js` - File metadata management (Home.vue workflow)
- `src/store/ocrConfig.js` - OCR API configuration management

### Utilities
- `src/utils/dbUtils.js` - IndexedDB operations for PDF data (OCR_PDF_DB)
- `src/utils/pdfUtils.js` - PDF.js parsing and thumbnail generation

### Components
- `src/components/PreviewSection.vue` - Zoomable PDF preview component
- `src/components/PDFPreviewModal.vue` - PDF preview modal

### Pages
- `src/pages/Home.vue` - Landing page with client-side PDF processing
- `src/pages/Files.vue` - File management with backend integration
- `src/pages/Workspace.vue` - Main OCR workspace
- `src/pages/Note.vue` - Note editor with AI chat
- `src/pages/NoteList.vue` - Note list view
- `src/pages/Settings.vue` - OCR configuration management

### Development Notes

1. **File Upload**: Two workflows exist:
   - **Home.vue**: Client-side processing via PDF.js, saves to IndexedDB and localStorage
   - **Files.vue**: Uploads to backend API (max 100MB), serves images from backend

2. **OCR Progress**: Tracked per file with `ocrProgress` and `proofProgress` percentages in localStorage

3. **State Persistence**: Uses localStorage for simple state, IndexedDB for complex data

4. **PDF.js Worker**: Configured to use CDN: `https://unpkg.com/pdfjs-dist@3.10.111/build/pdf.worker.js`

5. **Keyboard Navigation**:
   - Workspace supports arrow keys for page navigation when thumbnail list is focused
   - Ctrl+S saves content when Quill editor has focus

6. **Auto-save**:
   - Workspace saves selected page position to localStorage (`file_{fileId}_page`)
   - Selected page position is restored on component mount

7. **Text Processing**:
   - Workspace has a "处理标点" button that converts English punctuation to Chinese
   - Replaces: `,` → `，`, `"` → `”`, `~` → `～`, `(` → `（`, `)` → `）`, `?` → `？`, `:` → `：`, `;` → `；`, `!` → `！`, `.` → `。`

8. **Drag and Drop**:
   - Files.vue supports drag-and-drop upload with visual feedback
   - Uses drag counter to handle child element drag events correctly

9. **Image Fallback**: Workspace uses placeholder images from via.placeholder.com if image loading fails

### Common Issues

1. **OCR Failures**: If OCR fails, check Settings page for active configuration
2. **PDF Processing**: Two different workflows - client-side (Home) vs backend (Files)
3. **Large PDFs**: May impact performance; client-side processing can be memory-intensive
4. **Backend Required**: Backend must be running on `http://127.0.0.1:8000` for Files.vue workflow to work
5. **Image Loading**: Workspace uses placeholder images from via.placeholder.com if backend images fail to load
6. **LocalStorage Limits**: localStorage has ~5-10MB limit; IndexedDB used for larger data
7. **Blob URLs**: Home.vue creates blob URLs that should be revoked on unmount (handled in onBeforeUnmount)
8. **401 Redirects**: All 401 responses redirect to `/w/login` - ensure this route exists
9. **Path Aliases**: Use `@` for imports from `src/` directory

### Browser Support

Requires:
- IndexedDB support (for PDF data storage in dbUtils.js)
- File API (for drag-and-drop upload)
- Canvas API (for PDF thumbnail generation)
- ES6+ features (async/await, arrow functions, etc.)
- LocalStorage support (for configurations and metadata)

### Browser Compatibility

Modern browsers supporting:
- Vue 3 Composition API
- ES6+ JavaScript features
- IndexedDB API
- CSS Grid and Flexbox
- Transform-based animations
