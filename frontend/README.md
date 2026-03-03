# Swell Frontend

A fashion recommendation web application built with Next.js 16 and React 19. The frontend provides personalized outfit recommendations, virtual fitting room functionality, user closet management, and an AI-powered styling assistant.

## Project Overview

**Swell** is a full-stack fashion recommendation platform where users can:
- Browse personalized outfit recommendations with swipe interface
- Like/unlike outfits and save to favorites
- Set up preferences through a cold-start onboarding flow
- Use virtual fitting room to try outfits with photos
- Manage personal closet items
- Integrate with Google Gemini API for AI-powered outfit suggestions

**Technology Stack:**
- **Framework:** Next.js 16 with App Router
- **UI Library:** React 19
- **Styling:** Tailwind CSS v4 with PostCSS
- **HTTP Client:** Axios with automatic token injection
- **Language:** TypeScript
- **Fonts:** Google Fonts (Noto Sans KR for Korean, custom serif fonts)

## Getting Started

### Prerequisites

- Node.js 18+
- npm/yarn/pnpm
- Backend API running at `http://localhost:8000/api`

### Installation

```bash
npm install
```

### Running the Development Server

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser to see the application.

### Building for Production

```bash
npm run build
npm start
```

### Linting

```bash
npm run lint
```

## Project Structure

```
FE/
├── app/                      # Next.js App Router pages
│   ├── page.tsx             # Root landing page
│   ├── layout.tsx           # Root layout with fonts and metadata
│   ├── start/               # Authentication flow (login/signup)
│   ├── main/                # Recommendation feed (main dashboard)
│   ├── onboarding/          # Cold-start preference setup
│   ├── favorites/           # Liked outfits collection
│   └── closet/              # Virtual fitting room & closet management
├── components/              # React components (structure exists)
│   ├── common/              # Shared reusable components
│   ├── features/            # Feature-specific components
│   └── layout/              # Layout components
├── lib/                     # API client utilities and services
│   ├── api.ts              # Axios instance with interceptors
│   ├── auth.ts             # Authentication endpoints
│   ├── onboarding.ts       # Onboarding endpoints
│   ├── outfits.ts          # Outfit/recommendation endpoints
│   ├── profile.ts          # User profile endpoints
│   ├── closet.ts           # Closet management endpoints
│   ├── fitting.ts          # Virtual fitting endpoints
│   ├── user.ts             # Legacy user endpoints
│   └── favorites.ts        # Legacy favorites endpoints
├── hooks/                   # Custom React hooks
│   └── useAuth.ts          # Authentication status hook
├── types/                   # TypeScript type definitions
│   ├── index.ts            # Domain types (User, Tag, Coordi, Item)
│   └── api.ts              # API request/response types
├── public/                  # Static assets
│   └── images/             # Image assets
├── styles/                  # Global styles
│   └── globals.css         # Tailwind CSS imports
├── package.json            # Dependencies and scripts
├── tsconfig.json           # TypeScript configuration
├── tailwind.config.ts      # Tailwind CSS configuration
├── next.config.ts          # Next.js configuration
├── postcss.config.mjs      # PostCSS configuration
├── eslint.config.mjs       # ESLint configuration
└── README.md               # This file
```

## Pages and Routes

### Home (`/`)
- Simple landing page with welcome message
- Entry point for the application

### Authentication (`/start`)
- Login and signup form with toggleable UI
- Email, password, name, and gender fields
- Form validation with error messages
- 4-slide promotional guide carousel (Introduction → Swipe → Virtual Fitting → Call-to-action)
- Redirects to `/onboarding` for new users, `/main` for existing users with completed onboarding
- Background image: `start_bg.png`

### Recommendation Feed (`/main`)
- Main dashboard after login
- Split layout: 60% outfit card + 40% filters and product details
- Swipe-like card interface for browsing outfits
- **Season filters:** Spring, Summer, Fall, Winter
- **Style filters:** Casual, Minimal, Street, Sporty
- Like/unlike button (floating heart icon)
- Product list with brand, name, price
- "Add to closet" button for each product
- Outfit counter (current/total)
- Dropdown navigation menu (Profile, Favorites, Closet, Logout)

### Onboarding (`/onboarding`)
- 2-step cold-start preference setup
- **Step 1:** Select 3-10 preference tags
  - Available tags: casual, minimal, street, sporty, vintage, modern, classic, unique, simple, colorful, comfortable, sophisticated, personal, trendy, basic
- **Step 2:** Select exactly 5 outfits (coordis)
- Progress indicator and validation
- Submits data to backend and redirects to `/main`

### Favorites (`/favorites`)
- Grid layout (3 columns) of liked outfits
- Each outfit card shows image, style, season, description, and like date
- Unlike button on each card
- Empty state with emoji and link to browse more outfits

### Virtual Fitting Room (`/closet`)
- **Left panel (45%):** Fitting interface
  - Photo upload area with drag-and-drop UI
  - 3 clothing slots: Top (상의), Bottom (하의), Outer (아우터)
  - AI feedback message for fitted outfit
  - "Change photo" and "Start fitting" buttons
- **Right panel (55%):** Closet browser
  - Category filters: All, Top, Bottom, Outer
  - Grid display (3 columns) of saved closet items
  - Blue highlight with checkmark for selected items
  - Items can only be added to matching category slots

## API Integration

The frontend communicates with the backend API at `http://localhost:8000/api`. All API calls are centralized in the `lib/` directory:

### Authentication (`lib/auth.ts`)
- `signup(data)` - POST `/auth/signup`
- `login(data)` - POST `/auth/login` (stores JWT in sessionStorage)
- `logout()` - POST `/auth/logout`
- `getMe()` - GET `/auth/me`
- Utility: `isAuthenticated()`, `getToken()`, `clearToken()`

### Recommendations (`lib/outfits.ts`)
- `getRecommendations(params)` - GET `/outfits/recommendations`
- `getOutfitDetail(outfitId)` - GET `/outfits/{outfitId}`
- `addFavorite(outfitId)` - POST `/outfits/{outfitId}/favorite`
- `removeFavorite(outfitId)` - DELETE `/outfits/{outfitId}/favorite`
- `getFavorites(params)` - GET `/outfits/favorites`

### Onboarding (`lib/onboarding.ts`)
- `getTags()` - GET `/onboarding/tags`
- `getSampleCoordis(params)` - GET `/onboarding/sample-coordis`
- `submitOnboarding(data)` - POST `/onboarding`

### Profile (`lib/profile.ts`)
- `getProfile()` - GET `/profile`
- `updateProfile(data)` - PUT `/profile`
- `uploadProfilePhoto(photo)` - POST `/profile/photo`
- `updatePreferredTags(tagIds)` - PUT `/profile/tags`

### Closet Management (`lib/closet.ts`)
- `getClosetItems(params)` - GET `/closet`
- `addClosetItem(data)` - POST `/closet`
- `deleteClosetItem(itemId)` - DELETE `/closet/{itemId}`

### Virtual Fitting (`lib/fitting.ts`)
- `startFitting(data)` - POST `/virtual-fitting`
- `getFittingStatus(jobId)` - GET `/virtual-fitting/{jobId}/status`
- `getFittingHistory(params)` - GET `/virtual-fitting`
- `waitForFitting(jobId, options)` - Utility for polling with progress callback

## Custom Hooks

### `useAuth` (`hooks/useAuth.ts`)
Manages authentication state and user data:

```typescript
const { user, loading, setUser } = useAuth({ requireAuth: true });
```

- Checks sessionStorage for JWT token
- Fetches user info on mount
- Redirects to `/start` if not authenticated (when `requireAuth` is true)
- Returns: `{ user, loading, setUser }`

## TypeScript Types

### Domain Types (`types/index.ts`)
- **User** - User profile with preferences and onboarding status
- **Tag** - Style preference tag
- **Coordi** - Outfit/coordination with style, season, items
- **Item** - Product with brand, price, category, image

### API Types (`types/api.ts`)
- **ApiSuccessResponse<T>** - Typed API response wrapper
- **ApiErrorResponse** - Error response with message
- **Outfit** - Complete outfit with items and LLM recommendation
- **ClosetItem** - Saved closet item with category and season
- **FittingJob** - Virtual fitting job status
- **Gender** - "male" | "female"
- **Season** - "spring" | "summer" | "fall" | "winter"
- **Style** - "캐주얼" | "스포티" | "스트릿" | "미니멀"

## Styling

The project uses **Tailwind CSS v4** with custom configuration:

### Fonts
- **snippet** - Custom serif font for branding/logo
- **noto** - Noto Sans KR for Korean text
- **abyssinica** - Abyssinica SIL for English text

### Colors
- CSS custom properties: `--background`, `--foreground`
- Dark mode support via `prefers-color-scheme` media query
- Tailwind utilities: blue, pink, gray, white, black

### Global Styles (`styles/globals.css`)
- Tailwind CSS imports
- Custom font classes
- CSS variable definitions

## Key Implementation Details

### Authentication Flow
1. User logs in at `/start`
2. JWT token stored in `sessionStorage` (non-persistent)
3. Axios request interceptor automatically adds `Authorization: Bearer {token}` header
4. 401 responses trigger redirect to `/start`
5. New users redirected to `/onboarding`, existing users to `/main`

### State Management
- React hooks (useState, useRef, useEffect) for local component state
- No external state management library (Redux, Zustand, etc.)
- Mock data embedded in page components (temporary during development)

### Form Validation
- Email regex validation
- Password minimum 8 characters
- Password confirmation matching
- Tag selection limits (3-10)
- Outfit selection requirement (exactly 5)

### Onboarding Logic
- New users must complete 2-step onboarding
- Step 1: Select 3-10 tags
- Step 2: Select exactly 5 outfits
- Data persisted to backend

### Virtual Fitting
- Users upload photo and select clothing items
- Items organized by category (Top, Bottom, Outer)
- Backend processes fitting and returns AI recommendation
- Results shown with feedback message

## Browser Support

- Chrome/Edge 90+
- Firefox 88+
- Safari 14+
- Requires JavaScript enabled

## Environment Configuration

No environment variables required for basic development. The API base URL is hardcoded in `lib/api.ts`:

```typescript
baseURL: 'http://localhost:8000/api'
```

To change the API URL, modify the `api.ts` file.

## Development Notes

- **Components folder** structure exists but is unused - all UI currently in page files
- **Session-based auth** - Tokens not persisted across browser restart
- **Korean language support** - Full Korean text support via Noto Sans KR
- **Responsive design** - Layouts use percentage-based splits for responsiveness
- **Mock data** - Currently uses embedded mock data for demo (will be replaced with API calls)

## Additional Resources

- [Next.js Documentation](https://nextjs.org/docs)
- [React Documentation](https://react.dev)
- [Tailwind CSS Documentation](https://tailwindcss.com/docs)
- [TypeScript Documentation](https://www.typescriptlang.org/docs)
- [Axios Documentation](https://axios-http.com/docs)

## Backend Integration

The frontend expects a running backend at `http://localhost:8000/api`. For backend setup, see the main [README](../README.md) in the repository root or [BE/README.md](../BE/README.md).
