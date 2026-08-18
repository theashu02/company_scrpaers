# Deep Company Info Extraction Plan

To capture the detailed company data (such as exact funding stage, employee count history, business models, comprehensive descriptions, etc.), we need to hit the internal `_next/data` API that the Getro frontend uses when you click "View company".

Since manually clicking 500+ cards using Playwright would be extremely slow and error-prone, we will fetch this data asynchronously via direct HTTP calls, which will be much faster and cleaner.

## Proposed Changes

### `core/browser.py`
- **[MODIFY]** `HTTPClient`: Add an asynchronous fetch method (`async_fetch_json`) using `asyncio.to_thread` and `requests`. This allows us to fetch hundreds of company details concurrently without blocking the main event loop.
- **[MODIFY]** `BrowserManager`: Add a helper method to extract the Next.js `buildId` from a page's HTML (since this ID changes upon site deployments and is required for the deep API URLs).

### `scrapers/khosla.py` & `scrapers/accel.py`
- **[MODIFY]**: After the primary scraper collects all the basic company data via the list API interceptor, extract the unique `slug` for each company.
- **[MODIFY]**: Fetch the Next.js `buildId` for the site.
- **[MODIFY]**: Use `asyncio.gather` with a semaphore (to prevent rate-limiting) to concurrently fetch the detailed JSON for every single collected slug: `/_next/data/<buildId>/companies/<slug>.json?companySlug=<slug>`.
- **[MODIFY]**: Merge the resulting `pageProps.company` object into our `raw_responses` payload so the `DataTransformer` can process the rich data.

### `transformers/datatransform.py`
- **[MODIFY]** `CompanyModel` and `DataTransformer`: The transformer is already highly robust, but we will ensure that it properly extracts and maps the newly available deep fields (like `orgType`, `founded`, `approxEmployees`, `locations`, `organizationSizes`, etc.) to our standardized schema.

## User Review Required

> [!WARNING]  
> Fetching deep data for 500+ companies (like Accel) will send 500+ concurrent requests. I plan to use a semaphore limit of `10` concurrent requests to ensure we don't accidentally DDoS the site or get IP-banned. Let me know if you are comfortable with this rate limit or if you'd prefer to go faster/slower.

## Verification Plan

### Automated Verification
- I will run both the Khosla and Accel scrapers locally.
- Verify that the resulting CSV/JSON files contain the deep data (e.g., `approxEmployees`, `founded` year) that wasn't previously available from the list view.
