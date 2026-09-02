# PokiWrap download site

Vercel landing page with Windows and Mac download buttons.

```bash
npm install
npm run dev
```

## Deploy on Vercel

1. Push the PokiWrap repo to GitHub.
2. [New Vercel project](https://vercel.com/new) → import the repo.
3. Set **Root Directory** to `web`.
4. Add env var `NEXT_PUBLIC_GITHUB_REPO` = `yourname/PokiWrap`.
5. Deploy.

Download links then go to GitHub Releases (`PokiWrap-windows.exe` and `PokiWrap-mac.zip`). Create those with the **Release** GitHub Action (tag `v1.0.0` or run it manually).

Without GitHub Releases, put the binaries in `public/downloads/` and leave the env var empty.
