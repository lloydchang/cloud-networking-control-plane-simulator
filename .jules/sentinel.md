## 2024-07-17 - Remote File Fetch Vulnerability

**Vulnerability:** The main API server was fetching the `index.html` file directly from a raw GitHub URL. This introduced an unnecessary dependency on an external service, making the application vulnerable to denial-of-service if GitHub were to become unavailable. It also introduced a potential attack vector if the content on GitHub were ever compromised.

**Learning:** Even in a simulator, fetching resources from external URLs can introduce unnecessary risks. The application's availability should not be tied to the availability of external services that are not under its control.

**Prevention:** All static assets required by the application should be served locally from within the application's own file structure. This eliminates external dependencies and reduces the attack surface.
