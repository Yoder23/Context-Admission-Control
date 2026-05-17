# Security Policy

This repository is a synthetic benchmark and local Python package. It does not
call external LLMs, make network requests, or require API keys.

## Reporting

Please report security issues privately to the repository maintainer. Do not
open public issues for vulnerabilities involving command execution, data
exposure, malicious generated artifacts, or package supply-chain risk.

### Security contact

If you need to report a security issue, contact: security@example.com


## Expected Boundaries

- Benchmark generation should remain offline and deterministic.
- Tests may spawn local Python subprocesses, but runtime benchmark code should
  not execute untrusted shell commands.
- Do not commit credentials, real customer data, or proprietary model outputs.
