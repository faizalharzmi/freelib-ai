# Django request flow

A GET to `/` loads `home`; the search form sends `q` to `/search/`. `SearchForm` validates 2–200 characters and optional page 1–100. `run_search` invokes `SEARCH_GRAPH`, records duration and outcome in `SearchLog`, then the template displays retrieved books. `/api/search/` uses the same path and returns JSON. An invalid query returns HTTP 400.

Each results card links to `/book/?token=…`. Django signs the transient provider dictionary, and the detail view checks the signature and one-hour age. The token is not a database record. `/admin/` uses standard Django staff authentication; `/admin/analytics/` requires staff.
