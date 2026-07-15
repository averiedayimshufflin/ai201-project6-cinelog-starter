# PR Response Doc - CineLog Watchlist Feature

## AI Usage
I used Codex to orient myself in the codebase, compare the watchlist work against `services/collection_service.py` and `tests/test_collection.py`, run project-wide searches for watchlist names, install the test dependencies in an ignored local `.venv`, and verify the branch with pytest and git history checks. I also used Codex as a review partner for the design decisions below: the final positions are grounded in CineLog's existing collection behavior and the watchlist workflow in this repo.

## Comment 1 - Rename
**What I did:** The requested final service function is `add_to_watchlist()`, matching CineLog's `verb_to_noun` naming convention (`add_to_collection()`, `remove_from_collection()`, `get_collection()`). This checkout did not contain the original `feature/watchlist` branch or a `save_to_watchlist()` function, so I rebuilt the watchlist feature on a new `feature/watchlist` branch using the reviewed final name from the start. The route imports and calls `add_to_watchlist()` in `routes/watchlist.py`.

**How I verified:** I ran `rg -n "save_to_watchlist|add_to_watchlist|watchlist" -S app.py models.py routes services tests`. The search found `add_to_watchlist()` call sites and no remaining `save_to_watchlist` references.

## Comment 2 - Deduplication
**What I did:** I added a duplicate check in `add_to_watchlist()` before inserting a new `WatchlistEntry`. The code follows `add_to_collection()`'s pattern: validate that the `Film` exists, query for an existing entry with the same `user_id` and `film_id`, and raise `AlreadyInWatchlistError` if one exists. I also added a database-level unique constraint on `(user_id, film_id)` for the watchlist model so application logic and schema agree.

**How I verified:** I added `test_add_to_watchlist_duplicate_raises`, which adds the same film twice, expects `AlreadyInWatchlistError`, and confirms only one row exists. I also added `test_add_watchlist_route_duplicate_returns_conflict`, which verifies the endpoint returns HTTP 409 for the duplicate path.

## Comment 3 - Missing test
**What I did:** I created `tests/test_watchlist.py` and added `test_add_to_watchlist_nonexistent_film_raises`, modeled after `test_add_to_collection_nonexistent_film_raises`. It uses the same fixture style and a UUID-shaped missing film ID.

**How I verified:** I ran `.\\.venv\\Scripts\\python.exe -m pytest tests/test_watchlist.py -v` and `.\\.venv\\Scripts\\python.exe -m pytest tests/ -v`. The final full run passed: `13 passed`.

## Comment 4 - Default visibility
**My position:** Keep `public=True` as the default, but allow callers to override it explicitly with `public=False`.

**Reasoning:** CineLog is framed as a community film tracking app, so the default watchlist behavior should support sharing and discovery unless a caller opts out. A public default also matches the likely lightweight user flow for adding films: users can quickly build a watchlist without answering a visibility question every time. To avoid making privacy an all-or-nothing decision, I added the explicit `public` parameter to both the service and route so clients can make private entries intentionally.

**Tradeoff acknowledged:** The risk of a public default is that a user might add a film without realizing it is visible. A private default would be safer for sensitive use cases, but it would also make CineLog's social discovery behavior less useful and force clients to opt into the normal community-facing path. The compromise here is a visible default with explicit override support.

## Comment 5 - Sort order
**My position:** Use date-added descending for `get_watchlist()`.

**Reasoning:** Watchlists are about intent and recency: the film a user just saved is usually the one they expect to see first. This also matches the existing `get_collection()` behavior, which returns newest entries first. Keeping collection and watchlist ordering consistent reduces surprise across the API.

**Engagement with reviewer's point:** Alphabetical sorting is easier when users already know exactly which title they are looking for, and it can make long lists feel orderly. I still chose date-added because CineLog's API returns a feed-like list of saved films rather than a search index. If alphabetical browsing becomes important later, I would add an explicit `sort=title` option instead of changing the default.

## Comment 6 - Rebase
**What conflicted:** This fork did not have a local or remote `feature/watchlist` branch, so there was no pre-existing integer-ID watchlist code to conflict with. I created `feature/watchlist` from the current `origin/main`, which already includes the UUID refactor.

**How I resolved it:** I implemented watchlist code directly against the UUID model state. `WatchlistEntry.film_id` is `db.String(36)`, references `film.id`, and all tests use UUID-shaped IDs.

**How I verified no conflict remains:** I ran `git fetch origin` followed by `git rebase origin/main`; Git reported `Current branch feature/watchlist is up to date.` I also ran `git log --oneline --merges origin/main..HEAD`, which produced no merge commits.

## Stretch Features
**remove_from_watchlist():** I added `remove_from_watchlist(user_id, film_id)` following the `remove_from_collection()` pattern, plus route support at `DELETE /watchlist/<user_id>/remove`. Tests cover successful removal and the missing-entry error path.

**Second edge-case test:** I added route-level duplicate handling coverage because it verifies the service error is translated into the expected HTTP 409 response for API callers.

**Visibility toggle:** I added a `public` parameter to `add_to_watchlist()` and to `POST /watchlist/<user_id>/add`. Tests cover `public=False` at both the service and route layers.

## Git Log
Take the final screenshot after the `docs: add pr response for watchlist review` commit lands. The verified pre-docs branch log was:

```text
4a3a48d test: add watchlist route coverage
5e70932 test: add watchlist service coverage
7983889 feat: add watchlist service and endpoints
```

## PR Description
**Title:** Add watchlist feature

**Feature overview:** This PR adds a watchlist feature so CineLog users can save films they want to watch later without marking them as watched in their collection. It adds a UUID-based `WatchlistEntry` model, watchlist service functions, and REST endpoints for listing, adding, and removing watchlist films. The implementation prevents duplicate watchlist entries and returns clear API errors for missing films or conflicts.

**Design decisions:** I kept watchlist visibility public by default (`public=True`) because CineLog is a community film tracking app and shared watchlists support discovery. To address the privacy tradeoff, callers can explicitly set `{ "public": false }` when adding a film. I also chose newest-first sort order for `GET /watchlist/<user_id>` because watchlists are usually driven by recent intent, and this keeps the behavior consistent with the existing collection API.

**Manual testing steps:**
1. Install dependencies: `pip install -r requirements.txt`.
2. Start the Flask API: `python app.py`.
3. Create or identify one test user UUID and two film UUIDs in the database.
4. Add a public watchlist entry by sending `POST /watchlist/<user_id>/add` with body `{ "film_id": "<film_uuid>" }`.
5. Confirm the response is `201` and includes `"public": true`.
6. Add a private watchlist entry for a different film by sending `POST /watchlist/<user_id>/add` with body `{ "film_id": "<film_uuid>", "public": false }`.
7. Confirm the response is `201` and includes `"public": false`.
8. Fetch the watchlist with `GET /watchlist/<user_id>` and confirm the private entry appears before the earlier public entry because results are newest-first.
9. Send the same add request again for an existing watchlist film and confirm the API returns `409`.
10. Remove an entry by sending `DELETE /watchlist/<user_id>/remove` with body `{ "film_id": "<film_uuid>" }`.
11. Fetch `GET /watchlist/<user_id>` again and confirm the removed film no longer appears.

**Automated testing:**
```bash
pytest tests/ -v
```

Expected result: all collection and watchlist tests pass.
