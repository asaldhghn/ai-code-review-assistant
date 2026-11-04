# 04 · Frontend walkthrough

The frontend is a **single-page app**: the browser loads one HTML page, and JavaScript draws the screens. It is written in **React** (UI as functions called components) with **TypeScript** (JavaScript plus types that catch mistakes before the code runs), built by **Vite**, and styled with **Tailwind CSS** (small utility classes like `text-muted` instead of separate CSS files).

## Folder map (`frontend/src/`)

| Path | Purpose |
| --- | --- |
| `main.tsx` | Starts React and renders `<App />` |
| `App.tsx` | Chooses what to show: Workspace, Results or About |
| `types.ts` | TypeScript types that mirror the backend's JSON |
| `api.ts` | All `fetch` calls and error handling |
| `hooks/useReviewSession.ts` | The state and actions of the Workspace |
| `components/` | UI pieces (`Workspace`, `CodeEditor`, `Header`, `About`, ...) |
| `components/results/` | Results screen pieces (`Summary`, `Filters`, `FindingList`, `FindingDetail`, `CodeView`) |
| `lib/findings.ts` | Pure helper functions (filtering, counting) |
| `index.css` | Design tokens (colors, fonts) and global rules |

## Components and props

A component is a function that returns markup. Data flows **down** as props:

```tsx
<FindingList findings={visible} selectedId={activeId} onSelect={setSelectedId} />
```

`FindingList` does not know how selection is stored. It calls `onSelect(id)` and the parent updates its state. This "data down, events up" pattern keeps components simple and testable.

## State

State is data that changes over time and re-draws the screen when it does. `useState` is the basic tool:

```tsx
const [filters, setFilters] = useState<FindingFilters>(NO_FILTERS);
```

[useReviewSession.ts](../../frontend/src/hooks/useReviewSession.ts) is a **custom hook** that bundles everything the Workspace needs: the code, language, chosen reviewers, mode, API key, loading flag, error, and last result, plus actions like `run()` and `loadSample()`. Keeping this out of the components makes them mostly layout.

Two details worth understanding:

- **Derived state.** In `ResultsView`, the selected finding is *computed* (`visible.some(...) ? selectedId : visible[0]`) instead of synced with an effect. Fewer states means fewer bugs. The same idea fixed a lint error in `useReviewSession`: my first version used an effect to force `mode` to "demo" on demo-only servers, and ESLint's React rules rejected it, so the hook now derives `mode` from the config instead.
- **The API key lives only in React memory.** It is never put in `localStorage`, and `postReview()` sends it only as a header in live mode.

## Talking to the API

[api.ts](../../frontend/src/api.ts) wraps `fetch`:

- Adds a timeout and supports cancel via `AbortController`.
- Converts the backend's `{error:{code,message}}` into an `ApiError` class.
- Converts "could not reach the server" into a friendly message.

`ErrorBanner.tsx` then shows the message plus a hint keyed by error code (for example `invalid_credentials` suggests checking the key).

## The Workspace

`CodeEditor.tsx` is a plain `<textarea>` with a line-number gutter beside it; scrolling is synced in an `onScroll` handler. A plain textarea is fully accessible and adds no bundle weight (an editor like Monaco would add megabytes). `Ctrl+Enter` runs the review.

## The Results screen

- `Summary` shows real numbers from the response and a stacked bar whose widths are `count / total`. It has a text alternative (`role="img"` with an `aria-label`).
- `Filters` use buttons with `aria-pressed`, so screen readers announce which filter is on.
- `FindingDetail` renders `` `inline code` `` using `renderInline()`, which creates React elements. It never uses `innerHTML`, so model output cannot inject markup.
- `CodeView` marks lines that have findings and highlights the selected one.

## Accessibility choices

Semantic elements (`header`, `nav`, `main`, `section`, `article`, `fieldset`); every input has a label; focus rings come from one `:focus-visible` rule; severity is always shown with an icon **and** a word, never color alone; a "Skip to content" link; `prefers-reduced-motion` turns animations off.

## Commands

```bash
npm run dev        # dev server with hot reload
npm run build      # type-check + production bundle in dist/
npm run lint       # ESLint
npm run typecheck  # tsc only
npm test           # Vitest
```
