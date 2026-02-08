# 📚 GitHub Repository Management for MoneyBot

> **Saved Method for Future Use**  
> **Token Location:** `/root/.openclaw/workspace/.credentials/jarvis_accounts.env`  
> **Repository:** https://github.com/jarvisauto001-coder

---

## 🔑 GitHub Token

**Token:** `ghp_YOUR_TOKEN_HERE`  
**User:** `jarvisauto001-coder`  
**Scope:** Full repo access  
**Real Token Location:** `/root/.openclaw/workspace/.credentials/jarvis_accounts.env`

---

## 🚀 Method to Create New Repository

### Step 1: Prepare Local Directory
```bash
mkdir my-new-project
cd my-new-project
git init
git add .
git commit -m "Initial commit"
git branch -m main
```

### Step 2: Create Repo via GitHub API
```bash
export GITHUB_TOKEN="$(grep JARVIS_GITHUB_TOKEN /root/.openclaw/workspace/.credentials/jarvis_accounts.env | cut -d'=' -f2)"
GITHUB_USER="jarvisauto001-coder"
REPO_NAME="my-new-project"

curl -s -X POST \
  -H "Authorization: token $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github.v3+json" \
  -H "Content-Type: application/json" \
  https://api.github.com/user/repos \
  -d "{
    \"name\": \"$REPO_NAME\",
    \"description\": \"Project description\",
    \"private\": false,
    \"auto_init\": false
  }"
```

### Step 3: Push to GitHub
```bash
git remote add origin "https://${GITHUB_USER}:${GITHUB_TOKEN}@github.com/${GITHUB_USER}/${REPO_NAME}.git"
git push -u origin main
```

---

## 📂 Existing Repositories

| Repository | URL | Description |
|------------|-----|-------------|
| **moneybot-scripts** | https://github.com/jarvisauto001-coder/moneybot-scripts | Python automation scripts |

---

## 🔄 Update Existing Repository

```bash
cd /path/to/repo
git add .
git commit -m "Description of changes"
git push origin main
```

---

## ⚠️ Security Notes

- Token is stored in `/root/.openclaw/workspace/.credentials/jarvis_accounts.env`
- Never commit the token to GitHub!
- Token has full repo access - keep secure
- If token leaks, regenerate immediately at: https://github.com/settings/tokens

---

## 🆘 Troubleshooting

### Push Rejected (non-fast-forward)
```bash
git pull origin main --allow-unrelated-histories
# OR force push (overwrites remote):
git push -f origin main
```

### Authentication Failed
- Check token is valid: https://github.com/settings/tokens
- Verify token in env: `echo $GITHUB_TOKEN`
- Re-source credentials: `source /root/.openclaw/workspace/.credentials/jarvis_accounts.env`

---

**Document Created:** 2026-02-08  
**Last Updated:** 2026-02-08
