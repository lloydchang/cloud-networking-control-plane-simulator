
## 2024-07-22 - Playwright Verification Failures

**Learning:** When verifying static HTML files with Playwright, asynchronous operations like `fetch()` may fail instantly. To test loading states, simulate them by directly manipulating the DOM with `page.evaluate()` (e.g., adding a '.loading' class).

**Action:** For future frontend verification, I will use `page.evaluate()` to simulate the loading state when testing static files.
