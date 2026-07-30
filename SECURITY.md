# Security Policy

## Supported Versions

Security fixes are applied to the latest `main` branch and current container image tags published from it.

## Reporting a Vulnerability

Please report suspected vulnerabilities privately:

- Open a private security advisory in GitHub, or
- Email maintainers at `security@printdrop.local` (replace with your real security inbox).

Include:

- Affected version or image tag
- Impact summary
- Reproduction steps or proof of concept
- Suggested remediation if known

## Response Expectations

- Initial acknowledgement: within 72 hours
- Triage and severity assessment: within 7 days
- Fix timeline: based on severity and exploitability

## Disclosure

Please avoid public disclosure until a fix or mitigation is available and maintainers confirm coordinated release timing.

## Hardening Recommendations

- Run behind HTTPS reverse proxy
- Set `SECURE_COOKIES=true` only when the browser reaches PrintDrop over HTTPS
- Keep `SECURE_COOKIES=false` for plain HTTP Dockge (`:8000`) — secure cookies are dropped on HTTP and break login
- Use strong random values for `SESSION_SECRET` and `PRINT_API_KEY`
- Never put `PRINT_API_KEY` in browser JavaScript
- Restrict inbound access to trusted networks
- Keep Node.js dependencies and the base image patched

## Container Image Scanning

**Status (temporary):** The Trivy vulnerability scan gate and Trivy SPDX SBOM steps in `docker-publish` are currently **skipped** so image publish can succeed. Re-enable when image hardening is ready.

When re-enabled, the intended policy is:

- Fail the job on **fixable** `HIGH` and `CRITICAL` vulnerabilities (`severity: HIGH,CRITICAL`, `exit-code: 1`)
- Ignore vulns with no upstream fix yet (`ignore-unfixed: true`), which is common for Debian base packages outside app control
- Scan OS packages and language libraries (`vuln-type: os,library`)
- Upload SARIF to GitHub code scanning even when the severity gate fails
- Generate the SPDX SBOM with **Trivy** (not Anchore/Syft or BuildKit SBOM attestations), so vulnerability matching stays accurate

BuildKit SBOM attestations remain disabled (`sbom: false` on `docker/build-push-action`).
