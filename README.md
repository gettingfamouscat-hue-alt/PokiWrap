# PokiWrap

Desktop app that wraps Poki games as native Windows and Mac apps with each game’s logo. Games stream live from Poki — source files are not downloaded.

## Download site (Vercel)

The landing page lives in `web/`.

```bash
cd web
npm install
npm run dev
```

Deploy:

1. Push this repo to GitHub.
2. Import it in [Vercel](https://vercel.com/new).
3. Set **Root Directory** to `web`.
4. Optional: set `NEXT_PUBLIC_GITHUB_REPO` to `yourname/PokiWrap` so the buttons fetch the latest GitHub Release.

Without that env var, place binaries in `web/public/downloads/`:

- `PokiWrap-windows.exe`
- `PokiWrap-mac.zip`

Windows build copies the exe there automatically:

```bash
python -c "from pokiwrap.engine.exe import build_pokiwrap_exe; build_pokiwrap_exe()"
```

Mac CI produces `PokiWrap-mac.zip` via `.github/workflows/release.yml`.

## Run from source

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

## Usage

1. **Discover Games** — pick a catalog title or paste a Poki URL.
2. **Generate** — creates a native app on the Desktop with the game logo.
3. **Poki Account** — sign in so cloud progress and the ad blocker apply.
4. **My Apps** — launch or delete generated games.
