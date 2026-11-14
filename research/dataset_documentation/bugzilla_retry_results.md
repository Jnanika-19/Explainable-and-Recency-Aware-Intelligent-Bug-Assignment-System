# Bugzilla Bounded Retry Results

Retry date: 2026-11-11

## Scope and method

This report records only the four read-only requests listed in
`eclipse_project_source_probe.md`. The original URLs and `Invoke-WebRequest`
method were retained, including the 25-second timeout. Response-body parsing
was performed locally to check JSON validity and, if valid, the response
structure and requested product/bug metadata. No other API requests, downloads,
pagination, or collection were performed.

## Results

| Request | HTTP status | Content type | Temporary-shutdown HTML | Valid REST JSON | Request error |
|---|---:|---|---|---|---|
| `GET /rest/product/Platform` | 200 | `text/html` | Yes | No; JSON parsing failed | None |
| `GET /rest/product/PDE` | 200 | `text/html` | Yes | No; JSON parsing failed | None |
| `GET /rest/bug?product=Platform&limit=1&include_fields=id,product,component` | 200 | `text/html` | Yes | No; JSON parsing failed | None |
| `GET /rest/bug?product=PDE&limit=1&include_fields=id,product,component` | 200 | `text/html` | Yes | No; JSON parsing failed | None |

The four responses were HTML shutdown pages, not REST JSON. Therefore no
response structure or product/bug metadata could be verified.

## Outcome

The Eclipse Bugzilla source is still not usable for this proposed collection.
No bug records or comments were collected. Stop here; do not begin further
collection unless explicitly approved and the endpoints are verified to return
usable REST JSON.
