# Security Policy

## Supported Versions

Security fixes are applied to the default branch. Consumers should run the latest commit or latest tagged release when available.

## Reporting a Vulnerability

Do not open a public issue for suspected vulnerabilities. Use GitHub private vulnerability reporting if it is enabled for this repository, or contact the repository owner through their GitHub profile.

Please include:

- A clear description of the issue and affected recipe
- Reproduction steps or a minimal proof of concept
- Potential impact and any known mitigations
- Whether prompts, API keys, tool outputs, logs, or customer data may be exposed

## Security Expectations

- Never commit Cohere API keys, customer prompts, production logs, or evaluation datasets with private content.
- Keep recipe outputs synthetic unless the data source is explicitly public.
- Run local verification before merging:

```bash
python -m ruff check .
python -m compileall -q common recipes
```
