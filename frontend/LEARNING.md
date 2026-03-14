# Frontend Integration Learnings

These notes capture what went wrong during the dashboard session work and what future agents should do differently.

## 1. Use an explicit frontend API base URL

- The frontend should read `VITE_API_BASE_URL` from `frontend/.env`.
- Build full backend request URLs from that base in the API layer.
- Do not rely on Vite dev proxy behavior unless the repo explicitly uses it already.
- Current expected value:

```env
VITE_API_BASE_URL=http://127.0.0.1:8000
```

## 2. Match frontend API contracts to the real backend payload

- The backend sessions endpoint returns the backend session shape, not the old mock dashboard shape.
- Validate against the actual backend response first, then normalize into frontend domain models.
- Do not assume fields that look user-facing are non-null.

Important example from this task:

- Backend `label` can be `null`.
- Frontend schema must allow `label: string | null`.
- The adapter should convert `null` into a safe UI fallback such as `"Untitled session"`.

## 3. Normalize data before it reaches UI components

- Raw backend session data should not flow directly into widgets or pages.
- The current normalization path is:

1. `src/shared/api/sessions.ts` fetches and validates the raw API payload.
2. `src/entities/session/model/adapters.ts` converts backend sessions into `SessionNode`.
3. UI components consume only normalized `SessionNode` values.

- Keep this boundary intact.

## 4. Dashboard data flow

- Left panel:
  `GET /api/v1/sessions/`
  Returns root sessions where `parent_id` is null.

- Right canvas:
  `GET /api/v1/sessions/?parentId=<session-id>`
  Returns direct child sessions for the selected root session.

- The right canvas currently renders one node per session:
  the selected root session plus its direct children.

## 5. React hook order must stay stable

- `ChannelsPage` broke because `useState` was called only after early loading/error returns.
- Hooks must always be declared before any conditional return that might skip them on some renders.
- If selected state depends on fetched data, initialize the hook once and sync it with `useEffect`.

## 6. Add visible error and empty states

- A blank page is not acceptable for data-loading failures.
- Pages that depend on API data should distinguish between:
  - loading
  - API unreachable
  - valid empty result
  - partial child-query failure

## 7. Keep mock-era assumptions out of the live integration path

- The old dashboard was built around `fetchDashboardSnapshot()` mock data.
- Once switching to live endpoints, downstream consumers may still assume the old hook return shape.
- Search for all usages of shared hooks before changing their contract.

## 8. Practical rule for future agents

When integrating a new backend endpoint:

1. Inspect the real backend serializer/model first.
2. Update the frontend Zod schema to match the backend exactly.
3. Normalize backend nullability and naming differences in an adapter.
4. Only then wire the data into components.
5. Check all consumers of the changed hook or API helper.
6. Verify loading, empty, and error states.
