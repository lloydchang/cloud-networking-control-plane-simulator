## 2024-05-20 - Serve Static Assets Locally

**Vulnerability:** The application's main `index.html` was fetched from a raw GitHub URL. This created an availability risk (if GitHub was down) and an integrity risk (if the repo was compromised, malicious content could be served).

**Learning:** The application was implicitly trusting content served from an external source. While convenient for development, this is a security risk in a production or publicly-facing application.

**Prevention:** Always serve static assets from the local filesystem unless there is a compelling and well-vetted reason to do otherwise. This ensures the application controls the content it serves and is not dependent on the availability or security of a third-party service.
