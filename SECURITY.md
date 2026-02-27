# Security Policy

## 🔒 Reporting Security Issues

If you discover a security vulnerability, **DO NOT** open a public issue.

Instead, please email: **[Your Security Email]** or contact the repository owner directly.

---

## ⚠️ Critical: Never Share Credentials

**NEVER post in issues, PRs, or discussions:**

- ❌ Passwords
- ❌ API Tokens (Wiki.js, GitHub, Ollama, etc.)
- ❌ SSH Keys or Private Keys
- ❌ `.env` file contents
- ❌ Database credentials
- ❌ Authentication tokens of any kind

**Violation of this policy will result in:**
- Immediate issue/PR closure
- Potential ban from the repository
- Reporting to GitHub security team

---

## ✅ Safe to Share

You **can** safely share:

- ✅ Configuration examples (without credentials)
- ✅ Error messages (redact tokens/IPs if present)
- ✅ Feature requests
- ✅ Bug reports (without sensitive data)
- ✅ Questions about setup (use `.env.example` as reference)

---

## 🛡️ Security Best Practices

### For Contributors

1. **Never commit secrets**
   - Always use `.env` files (ignored by git)
   - Use `.env.example` for documentation
   - Review diffs before pushing

2. **Use GitHub Secret Scanning**
   - Enabled by default on this repo
   - Automatically detects leaked tokens

3. **Rotate compromised credentials**
   - If you accidentally commit a secret, rotate it immediately
   - Update `.env` file
   - Notify maintainers

### For Users

1. **Protect your `.env` file**
   - Never share it publicly
   - Use restrictive file permissions: `chmod 600 .env`
   - Keep backups encrypted

2. **Use strong credentials**
   - Generate API tokens with minimal required permissions
   - Rotate tokens periodically
   - Use different tokens for dev/prod

3. **Monitor access logs**
   - Check Wiki.js access logs for suspicious activity
   - Monitor Ollama API usage
   - Review GitHub repository access

---

## 🚨 What to Do If Credentials Are Leaked

1. **Rotate immediately**
   - Wiki.js: Revoke and create new API token
   - GitHub: Revoke PAT and create new one
   - Ollama: Change API key if applicable

2. **Notify maintainers**
   - Create a **private** security advisory
   - Email repository owner

3. **Review access logs**
   - Check if leaked credentials were used
   - Look for unauthorized access

4. **Update documentation**
   - Remind users to rotate their tokens
   - Update security guidance if needed

---

## 📋 Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| Latest  | ✅ Yes             |
| Older   | ❌ No (upgrade!)   |

We only support the latest release. Please upgrade to the newest version for security patches.

---

## 🔐 Security Features in This Project

- ✅ Environment variable configuration (no hardcoded secrets)
- ✅ `.gitignore` excludes `.env` and sensitive files
- ✅ `.env.example` provided for safe reference
- ✅ GitHub Secret Scanning enabled
- ✅ Dependency scanning via Dependabot (if enabled)

---

## 📧 Contact

For security-related questions or to report vulnerabilities:

- **Private Security Report:** Use GitHub's "Report a vulnerability" feature
- **Email:** [Your Security Contact Email]
- **Urgent:** Contact repository owner directly

---

**Remember: Security is everyone's responsibility. Thank you for keeping this project safe!** 🔒
