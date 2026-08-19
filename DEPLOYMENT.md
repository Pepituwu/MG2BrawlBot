# Deployment Guide

Automatic deployment via GitHub Actions to Portainer/Docker Swarm.

## Architecture

```
release published ──> build & push image to GHCR ──> call Portainer webhook ──> service updates
```

## Setup Instructions

### 1. Docker Swarm Stack Deployment

Deploy the stack in Portainer:

1. **Stacks** → **Add stack**
2. Paste the contents of `docker-compose.yml`
3. Set the stack name (e.g., `mg2brawlbot`)
4. Add stack environment variables:
   - `DISCORD_TOKEN` — your Discord bot token (required)
   - `BH_API_KEY` — Brawlhalla API key (required)
5. **Deploy the stack**

### 2. Enable Webhook on Service

This is what makes deployment automatic:

1. In Portainer: **Stacks** → your stack → **mg2brawlbot** service
2. On the service detail page, enable **Webhook**
3. Portainer generates a URL like `https://<portainer-host>/api/webhooks/<uuid>`
4. **Copy that URL**

### 3. Add GitHub Actions Secret

1. Go to your GitHub repository
2. **Settings** → **Secrets and variables** → **Actions**
3. **New repository secret**
   - Name: `PORTAINER_WEBHOOK_URL`
   - Value: paste the webhook URL from step 2

### 4. Automatic Deployment

Now when you publish a release on GitHub:

1. GitHub Actions builds the multiarch Docker image
2. Pushes to GHCR
3. Calls the Portainer webhook
4. Portainer forces a service update (pulls latest `:latest` tag)
5. Docker Swarm re-deploys with the new image automatically

**No manual intervention needed!**

## Triggering a Deployment

### Option A: GitHub Release (Recommended)

```bash
git tag v1.0.0
git push origin v1.0.0
```

Then create a release on GitHub. This triggers the full workflow including the webhook.

### Option B: Manual Push to Main

Pushes to `main` trigger the build and validation, but **NOT** the webhook (no auto-deployment).

## Image Registry

Images are pushed to:
- `ghcr.io/pepituwu/mg2brawlbot:latest`
- `ghcr.io/pepituwu/mg2brawlbot:<release-tag>`
- `ghcr.io/pepituwu/mg2brawlbot:<commit-sha>`

If the package is private, add a registry in Portainer:
1. **Registries** → **Add registry** → **Custom registry**
2. URL: `ghcr.io`
3. Username: your GitHub username
4. Password: a GitHub Personal Access Token with `read:packages` scope

## Troubleshooting

- **Webhook secret not set?** The workflow warns and skips the webhook gracefully
- **Portainer webhook failing?** Check that the webhook URL is correct and Portainer is accessible
- **Image pull failing?** If the GHCR package is private, make sure the registry credentials are configured in Portainer
