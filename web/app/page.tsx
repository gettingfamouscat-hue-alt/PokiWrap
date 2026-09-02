import { DownloadButtons } from "./DownloadButtons";

export default function HomePage() {
  return (
    <div className="wrap">
      <header className="nav">
        <div className="brand">
          <span className="mark" aria-hidden="true" />
          PokiWrap
        </div>
      </header>

      <main>
        <section className="hero">
          <p className="kicker">Desktop wrappers for Poki</p>
          <h1>Play Poki games like real apps.</h1>
          <p className="lede">
            Generate native Windows and Mac apps from any Poki title. Games stream live, fill the
            window, sync cloud progress, and run with an ad blocker.
          </p>
          <DownloadButtons />
        </section>

        <section className="features">
          <article className="feature">
            <h3>Game-only window</h3>
            <p>Hides the Poki site chrome so the game fills your desktop window.</p>
          </article>
          <article className="feature">
            <h3>Cloud progress</h3>
            <p>Connect your Poki account once and wrappers load your saves.</p>
          </article>
          <article className="feature">
            <h3>Ad blocker</h3>
            <p>EasyList + EasyPrivacy style blocking, on by default.</p>
          </article>
        </section>
      </main>

      <footer className="footer">PokiWrap is unofficial and not affiliated with Poki.</footer>
    </div>
  );
}
