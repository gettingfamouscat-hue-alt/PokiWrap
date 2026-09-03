"""Compile a native Windows game .exe (Edge WebView2) with the game logo."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

from pokiwrap.engine.account import FIND_USER_JS
from pokiwrap.engine.shortcut import _safe_shortcut_name
from pokiwrap.engine.template import AD_SKIP_JS, CHROME_HIDE_JS, FS_KEY_JS
from pokiwrap.engine.webview2 import ensure_webview2
from pokiwrap.paths import (
    account_cookies_path,
    account_profile_dir,
    account_state_path,
    adblock_domains_path,
    assets_dir,
    desktop_dir,
    python_executable,
    runtime_dir,
    settings_path,
)

PLAYER_CS = """\
using System;
using System.Collections.Generic;
using System.Drawing;
using System.IO;
using System.Reflection;
using System.Runtime.InteropServices;
using System.Text;
using System.Threading.Tasks;
using System.Windows.Forms;
using Microsoft.Web.WebView2.Core;
using Microsoft.Web.WebView2.WinForms;

internal static class Native
{{
    [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    public static extern bool SetDllDirectory(string lpPathName);

    [DllImport("shell32.dll", CharSet = CharSet.Unicode)]
    public static extern int SetCurrentProcessExplicitAppUserModelID(string AppID);
}}

internal static class Program
{{
    [STAThread]
    static void Main()
    {{
        string runtime = {runtime};
        Native.SetDllDirectory(runtime);
        Native.SetCurrentProcessExplicitAppUserModelID({app_id});
        AppDomain.CurrentDomain.AssemblyResolve += delegate(object sender, ResolveEventArgs args)
        {{
            try
            {{
                string file = new AssemblyName(args.Name).Name + ".dll";
                string path = Path.Combine(runtime, file);
                if (File.Exists(path))
                    return Assembly.LoadFrom(path);
            }}
            catch {{ }}
            return null;
        }};
        Application.EnableVisualStyles();
        Application.SetCompatibleTextRenderingDefault(false);
        try
        {{
            Application.Run(new GameForm());
        }}
        catch (Exception ex)
        {{
            MessageBox.Show(ex.Message, "PokiWrap");
        }}
    }}
}}

internal sealed class GameForm : Form
{{
    bool fullScreen;
    Rectangle windowedBounds;
    FormWindowState windowedState;
    FormBorderStyle windowedBorder = FormBorderStyle.Sizable;
    int lastToggleTick;

    public GameForm()
    {{
        Text = {app_name};
        Width = 1280;
        Height = 760;
        MinimumSize = new Size(800, 500);
        StartPosition = FormStartPosition.CenterScreen;
        BackColor = Color.Black;
        KeyPreview = true;
        KeyDown += delegate(object sKey, KeyEventArgs eKey)
        {{
            if (eKey.KeyCode == Keys.F11)
            {{
                eKey.Handled = true;
                _ToggleFullScreen();
            }}
            else if (eKey.KeyCode == Keys.Escape && fullScreen)
            {{
                eKey.Handled = true;
                _ToggleFullScreen();
            }}
        }};
        try
        {{
            if (File.Exists({icon_path}))
                Icon = new Icon({icon_path});
        }}
        catch {{ }}

        string userData = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "PokiWrap", "account_webview");
        Directory.CreateDirectory(userData);

        Label loading = new Label();
        loading.Text = "Loading " + {app_name} + "...";
        loading.Dock = DockStyle.Fill;
        loading.TextAlign = ContentAlignment.MiddleCenter;
        loading.ForeColor = Color.White;
        loading.BackColor = Color.Black;
        loading.Font = new Font("Segoe UI", 16f);
        Controls.Add(loading);

        WebView2 web = new WebView2();
        web.Dock = DockStyle.Fill;
        web.DefaultBackgroundColor = Color.Black;
        web.CreationProperties = new CoreWebView2CreationProperties();
        web.CreationProperties.UserDataFolder = userData;
        web.CreationProperties.AdditionalBrowserArguments =
            "--autoplay-policy=no-user-gesture-required --ignore-gpu-blocklist --disable-features=ThirdPartyStoragePartitioning,TrackingPrevention,msWebView2EnableTrackingPrevention";
        Controls.Add(web);
        web.SendToBack();

        Load += delegate
        {{
            web.EnsureCoreWebView2Async(null);
        }};

        web.CoreWebView2InitializationCompleted += delegate(object sender, CoreWebView2InitializationCompletedEventArgs e)
        {{
            if (!e.IsSuccess)
            {{
                MessageBox.Show(
                    "Microsoft Edge WebView2 is required to run this game.\\n\\n" +
                    (e.InitializationException == null ? "" : e.InitializationException.Message),
                    {app_name});
                Close();
                return;
            }}
            try
            {{
                File.AppendAllText(Path.Combine(userData, "pokiwrap.log"), DateTime.Now.ToString("s") + " webview ready\\r\\n");
            }}
            catch {{ }}
            web.CoreWebView2.Settings.AreDefaultContextMenusEnabled = false;
            web.CoreWebView2.Settings.AreDevToolsEnabled = false;
            web.CoreWebView2.Settings.IsStatusBarEnabled = false;
            web.CoreWebView2.Settings.IsZoomControlEnabled = false;
            web.CoreWebView2.Settings.IsWebMessageEnabled = true;
            try {{ web.CoreWebView2.Settings.AreBrowserAcceleratorKeysEnabled = false; }} catch {{ }}
            web.CoreWebView2.Settings.UserAgent =
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0";
            web.CoreWebView2.PermissionRequested += delegate(object sPerm, CoreWebView2PermissionRequestedEventArgs ePerm)
            {{
                ePerm.Handled = true;
                ePerm.State = CoreWebView2PermissionState.Allow;
            }};
            try
            {{
                FieldInfo field = typeof(WebView2).GetField("_coreWebView2Controller", BindingFlags.Instance | BindingFlags.NonPublic);
                CoreWebView2Controller controller = field == null ? null : field.GetValue(web) as CoreWebView2Controller;
                if (controller != null)
                {{
                    controller.AcceleratorKeyPressed += delegate(object sAcc, CoreWebView2AcceleratorKeyPressedEventArgs eAcc)
                    {{
                        if (eAcc.VirtualKey != 122)
                            return;
                        eAcc.Handled = true;
                        if (eAcc.KeyEventKind == CoreWebView2KeyEventKind.KeyDown)
                            _ToggleFullScreen();
                    }};
                }}
            }}
            catch {{ }}
            web.CoreWebView2.ContainsFullScreenElementChanged += delegate
            {{
                if (web.CoreWebView2.ContainsFullScreenElement != fullScreen)
                    _ToggleFullScreen();
            }};
            AdBlock.Attach(web.CoreWebView2, {adblock_list}, {adblock_settings});
            web.CoreWebView2.NavigationStarting += delegate(object sStart, CoreWebView2NavigationStartingEventArgs eStart)
            {{
                if (AdBlock.IsAdRequest(eStart.Uri) || _IsOtherPokiGame(eStart.Uri, {target_slug}))
                    eStart.Cancel = true;
            }};
            web.CoreWebView2.FrameNavigationStarting += delegate(object sFrame, CoreWebView2NavigationStartingEventArgs eFrame)
            {{
                if (AdBlock.IsAdRequest(eFrame.Uri) || _IsOtherPokiGame(eFrame.Uri, {target_slug}))
                    eFrame.Cancel = true;
            }};
            web.CoreWebView2.WebMessageReceived += delegate(object sMsg, CoreWebView2WebMessageReceivedEventArgs eMsg)
            {{
                loading.Visible = false;
                web.BringToFront();
                string msg = "";
                try {{ msg = eMsg.TryGetWebMessageAsString(); }} catch {{ }}
                if (msg == "f11")
                    _ToggleFullScreen();
                else if (msg == "esc" && fullScreen)
                    _ToggleFullScreen();
            }};
            web.CoreWebView2.NavigationCompleted += delegate(object sNav, CoreWebView2NavigationCompletedEventArgs eNav)
            {{
                try
                {{
                    File.AppendAllText(
                        Path.Combine(userData, "pokiwrap.log"),
                        DateTime.Now.ToString("s") + " nav " + web.CoreWebView2.Source + " ok=" + eNav.IsSuccess + "\\r\\n");
                }}
                catch {{ }}
                web.CoreWebView2.ExecuteScriptAsync({fill_js});
            }};
            web.CoreWebView2.NewWindowRequested += delegate(object sWin, CoreWebView2NewWindowRequestedEventArgs eWin)
            {{
                eWin.Handled = true;
                string popup = eWin.Uri ?? "";
                if (_IsOAuth(popup))
                {{
                    try {{ web.CoreWebView2.Navigate(popup); }} catch {{ }}
                }}
            }};
            web.CoreWebView2.AddScriptToExecuteOnDocumentCreatedAsync({fill_js});
            web.CoreWebView2.AddScriptToExecuteOnDocumentCreatedAsync({ad_js});
            web.CoreWebView2.AddScriptToExecuteOnDocumentCreatedAsync({fs_js});
            Timer iso = new Timer();
            iso.Interval = 500;
            iso.Tick += delegate(object sIso, EventArgs eIso)
            {{
                try
                {{
                    if (web.CoreWebView2 != null)
                        web.CoreWebView2.ExecuteScriptAsync({fill_js});
                }}
                catch {{ }}
            }};
            iso.Start();
            Action go = delegate
            {{
                Action start = delegate {{ web.CoreWebView2.Navigate({page_url}); }};
                if ({page_url}.IndexOf("poki.com", StringComparison.OrdinalIgnoreCase) >= 0)
                    _PrepareWebsiteSave(web, {cookies_path}, {account_path}, start);
                else
                    start();
            }};
            if (IsHandleCreated)
                BeginInvoke(go);
            else
                HandleCreated += delegate {{ BeginInvoke(go); }};
            Timer hide = new Timer();
            hide.Interval = 8000;
            hide.Tick += delegate(object sHide, EventArgs eHide)
            {{
                hide.Stop();
                loading.Visible = false;
                web.BringToFront();
            }};
            hide.Start();
        }};
    }}

    void _ToggleFullScreen()
    {{
        int now = Environment.TickCount;
        if (lastToggleTick != 0 && now - lastToggleTick < 350)
            return;
        lastToggleTick = now;
        if (!fullScreen)
        {{
            windowedBounds = Bounds;
            windowedState = WindowState;
            windowedBorder = FormBorderStyle;
            WindowState = FormWindowState.Normal;
            FormBorderStyle = FormBorderStyle.None;
            Bounds = Screen.FromControl(this).Bounds;
            fullScreen = true;
            return;
        }}
        FormBorderStyle = windowedBorder;
        WindowState = windowedState;
        Bounds = windowedBounds;
        fullScreen = false;
    }}

    protected override bool ProcessCmdKey(ref Message msg, Keys keyData)
    {{
        if (keyData == Keys.F11)
        {{
            _ToggleFullScreen();
            return true;
        }}
        if (keyData == Keys.Escape && fullScreen)
        {{
            _ToggleFullScreen();
            return true;
        }}
        return base.ProcessCmdKey(ref msg, keyData);
    }}

    static bool _IsOAuth(string uri)
    {{
        string text = (uri ?? "").ToLowerInvariant();
        return text.IndexOf("accounts.google.") >= 0
            || text.IndexOf("appleid.apple") >= 0
            || text.IndexOf("login.live") >= 0
            || text.IndexOf("login.microsoftonline") >= 0
            || text.IndexOf("firebaseapp") >= 0
            || text.IndexOf("identitytoolkit") >= 0;
    }}

    static bool _IsOtherPokiGame(string uri, string slug)
    {{
        try
        {{
            if (string.IsNullOrEmpty(uri) || string.IsNullOrEmpty(slug))
                return false;
            Uri parsed = new Uri(uri);
            string path = parsed.AbsolutePath ?? "";
            int crazy = path.IndexOf("/game/", StringComparison.OrdinalIgnoreCase);
            int poki = path.IndexOf("/g/", StringComparison.OrdinalIgnoreCase);
            int index;
            int skip;
            if (crazy >= 0)
            {{
                index = crazy;
                skip = 6;
            }}
            else if (poki >= 0)
            {{
                index = poki;
                skip = 3;
            }}
            else
                return false;
            string rest = path.Substring(index + skip).Trim('/');
            if (rest.Length == 0)
                return false;
            string other = rest.Split('/')[0];
            int q = other.IndexOf('?');
            if (q >= 0)
                other = other.Substring(0, q);
            return !other.Equals(slug, StringComparison.OrdinalIgnoreCase);
        }}
        catch {{ }}
        return false;
    }}

    static bool _HasLinkedAccount(string accountFile, string cookieFile)
    {{
        try
        {{
            if (File.Exists(cookieFile) && new FileInfo(cookieFile).Length > 0)
                return true;
            if (!File.Exists(accountFile))
                return false;
            string text = File.ReadAllText(accountFile);
            if (text.IndexOf("\\"connected\\": true") >= 0 || text.IndexOf("\\"connected\\":true") >= 0)
                return true;
            string[] lines = text.Split(new char[] {{ '\\n' }});
            return lines.Length > 0 && lines[0].Trim() == "1";
        }}
        catch {{ }}
        return false;
    }}

    static void _PrepareWebsiteSave(WebView2 web, string cookieFile, string accountFile, Action done)
    {{
        CoreWebView2 core = web.CoreWebView2;
        Action finish = delegate
        {{
            _ImportPokiCookies(core, cookieFile);
            if (done != null) done();
        }};
        if (core == null || !_HasLinkedAccount(accountFile, cookieFile))
        {{
            finish();
            return;
        }}
        try
        {{
            CoreWebView2Profile profile = core.Profile;
            CoreWebView2BrowsingDataKinds kinds =
                CoreWebView2BrowsingDataKinds.IndexedDb
                | CoreWebView2BrowsingDataKinds.LocalStorage
                | CoreWebView2BrowsingDataKinds.CacheStorage;
            profile.ClearBrowsingDataAsync(kinds).ContinueWith(
                delegate(Task task)
                {{
                    try
                    {{
                        if (web.IsHandleCreated)
                            web.BeginInvoke(finish);
                        else
                            finish();
                    }}
                    catch
                    {{
                        try {{ finish(); }} catch {{ }}
                    }}
                }});
            return;
        }}
        catch {{ }}
        finish();
    }}

    static void _ImportPokiCookies(CoreWebView2 core, string cookieFile)
    {{
        try
        {{
            if (core == null || !File.Exists(cookieFile))
                return;
            string[] lines = File.ReadAllLines(cookieFile);
            for (int i = 0; i < lines.Length; i++)
            {{
                try
                {{
                    string line = lines[i].Trim();
                    if (line.Length == 0)
                        continue;
                    string[] parts = line.Split('\t');
                    if (parts.Length < 8)
                        continue;
                    string name = parts[0];
                    string domain = parts[1];
                    string path = string.IsNullOrEmpty(parts[2]) ? "/" : parts[2];
                    if (string.IsNullOrEmpty(name) || string.IsNullOrEmpty(domain))
                        continue;
                    if (domain.IndexOf("poki", StringComparison.OrdinalIgnoreCase) < 0
                        && domain.IndexOf("google", StringComparison.OrdinalIgnoreCase) < 0
                        && domain.IndexOf("firebase", StringComparison.OrdinalIgnoreCase) < 0
                        && domain.IndexOf("apple", StringComparison.OrdinalIgnoreCase) < 0)
                        continue;
                    string value = Encoding.UTF8.GetString(Convert.FromBase64String(parts[7]));
                    CoreWebView2Cookie cookie = core.CookieManager.CreateCookie(name, value, domain, path);
                    cookie.IsHttpOnly = parts[3] == "1";
                    cookie.IsSecure = parts[4] == "1" || name.StartsWith("__Secure") || name.StartsWith("__Host");
                    cookie.SameSite = cookie.IsSecure
                        ? CoreWebView2CookieSameSiteKind.None
                        : CoreWebView2CookieSameSiteKind.Lax;
                    double expires = 0;
                    double.TryParse(parts[6], System.Globalization.NumberStyles.Float, System.Globalization.CultureInfo.InvariantCulture, out expires);
                    if (parts[5] != "1" && expires > 0)
                        cookie.Expires = new DateTime(1970, 1, 1, 0, 0, 0, DateTimeKind.Utc).AddSeconds(expires).ToLocalTime();
                    core.CookieManager.AddOrUpdateCookie(cookie);
                }}
                catch {{ }}
            }}
        }}
        catch {{ }}
    }}
}}
"""


def _adblock_source() -> Path:
    here = Path(__file__).resolve().parent
    candidates = [here / "adblock_host.cs"]
    if getattr(sys, "frozen", False):
        meipass = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
        candidates.extend(
            [
                meipass / "pokiwrap" / "engine" / "adblock_host.cs",
                meipass / "adblock_host.cs",
            ]
        )
    for path in candidates:
        if path.exists():
            return path
    raise RuntimeError("Missing adblock_host.cs")


def _csc_path() -> Path | None:
    windir = Path(os.environ.get("WINDIR", r"C:\Windows"))
    for candidate in (
        windir / "Microsoft.NET" / "Framework64" / "v4.0.30319" / "csc.exe",
        windir / "Microsoft.NET" / "Framework" / "v4.0.30319" / "csc.exe",
    ):
        if candidate.exists():
            return candidate
    return None


def _csharp_string(value: str) -> str:
    return "@\"" + value.replace("\"", "\"\"") + "\""


def build_game_exe(
    app_name: str,
    folder: Path,
    icon_path: Path | None,
    game_url: str,
    page_url: str | None = None,
) -> Path | None:
    if sys.platform != "win32":
        return None
    csc = _csc_path()
    if csc is None:
        return None

    webview = ensure_webview2()
    exe_name = _safe_shortcut_name(app_name) + ".exe"
    exe_path = folder / exe_name
    source_path = folder / "_player.cs"
    icon = icon_path if icon_path and icon_path.exists() else folder / "icon.ico"
    page = page_url or game_url
    slug = page.rstrip("/").split("/")[-1].split("?")[0]
    isolate = CHROME_HIDE_JS.replace("__TARGET_SLUG__", slug)
    try:
        from pokiwrap.engine.adblock import ensure_adblock_list
        ensure_adblock_list()
    except Exception:
        pass
    source_path.write_text(
        PLAYER_CS.format(
            runtime=_csharp_string(str(webview.resolve())),
            app_id=_csharp_string("PokiWrap." + _safe_shortcut_name(app_name).replace(" ", "")),
            app_name=_csharp_string(app_name),
            icon_path=_csharp_string(str(icon.resolve()) if icon.exists() else ""),
            fill_js=_csharp_string(isolate),
            ad_js=_csharp_string(AD_SKIP_JS),
            target_slug=_csharp_string(slug),
            game_url=_csharp_string(game_url),
            page_url=_csharp_string(page),
            cookies_path=_csharp_string(str(account_cookies_path())),
            account_path=_csharp_string(str(account_state_path())),
            adblock_list=_csharp_string(str(adblock_domains_path())),
            adblock_settings=_csharp_string(str(settings_path())),
            fs_js=_csharp_string(FS_KEY_JS),
        ),
        encoding="utf-8",
    )

    core = webview / "Microsoft.Web.WebView2.Core.dll"
    winforms = webview / "Microsoft.Web.WebView2.WinForms.dll"
    command = [
        str(csc),
        "/nologo",
        "/optimize+",
        "/target:winexe",
        "/platform:x64",
        "/r:System.Windows.Forms.dll",
        "/r:System.Drawing.dll",
        f"/r:{core}",
        f"/r:{winforms}",
        f"/out:{exe_path}",
        str(source_path),
        str(_adblock_source()),
    ]
    if icon.exists():
        command.insert(command.index(str(source_path)), f"/win32icon:{icon}")

    completed = subprocess.run(command, capture_output=True, text=True)
    if completed.returncode != 0 and icon.exists():
        command = [arg for arg in command if not arg.startswith("/win32icon:")]
        completed = subprocess.run(command, capture_output=True, text=True)
    try:
        source_path.unlink(missing_ok=True)
    except OSError:
        pass
    if completed.returncode != 0 or not exe_path.exists():
        raise RuntimeError(
            completed.stderr.strip()
            or completed.stdout.strip()
            or "Failed to compile the native game .exe."
        )
    return exe_path


def publish_desktop_exe(exe_path: Path, app_name: str) -> Path:
    desktop = desktop_dir()
    desktop.mkdir(parents=True, exist_ok=True)
    stem = _safe_shortcut_name(app_name)
    dest = desktop / f"{stem}.exe"
    shutil.copy2(exe_path, dest)
    old_lnk = desktop / f"{stem}.lnk"
    try:
        if old_lnk.exists():
            old_lnk.unlink()
    except OSError:
        pass
    return dest


DETECT_JS = (
    "(function () {\n"
    "  function ping() {\n"
    "    try {\n"
    "      var result = "
    + FIND_USER_JS.strip()
    + ";\n"
    "      window.chrome.webview.postMessage(result);\n"
    "    } catch (e) {}\n"
    "  }\n"
    "  ping();\n"
    "  setInterval(ping, 800);\n"
    "})();\n"
)

LOGIN_CS = """\
using System;
using System.Collections.Generic;
using System.Drawing;
using System.IO;
using System.Reflection;
using System.Runtime.InteropServices;
using System.Text;
using System.Threading.Tasks;
using System.Windows.Forms;
using Microsoft.Web.WebView2.Core;
using Microsoft.Web.WebView2.WinForms;

internal static class Native
{{
    [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    public static extern bool SetDllDirectory(string lpPathName);

    [DllImport("shell32.dll", CharSet = CharSet.Unicode)]
    public static extern int SetCurrentProcessExplicitAppUserModelID(string AppID);
}}

internal static class Program
{{
    [STAThread]
    static void Main(string[] args)
    {{
        string runtime = {runtime};
        Native.SetDllDirectory(runtime);
        Native.SetCurrentProcessExplicitAppUserModelID("PokiWrap.Account");
        AppDomain.CurrentDomain.AssemblyResolve += delegate(object sender, ResolveEventArgs e)
        {{
            try
            {{
                string file = new AssemblyName(e.Name).Name + ".dll";
                string path = Path.Combine(runtime, file);
                if (File.Exists(path))
                    return Assembly.LoadFrom(path);
            }}
            catch {{ }}
            return null;
        }};
        Application.EnableVisualStyles();
        Application.SetCompatibleTextRenderingDefault(false);
        bool signout = false;
        for (int i = 0; i < args.Length; i++)
        {{
            if (args[i] == "--signout")
                signout = true;
        }}
        if (signout)
            Application.Run(new SignOutForm());
        else
            Application.Run(new LoginForm());
    }}
}}

internal static class AccountStore
{{
    public static void WriteAccount(string path, bool connected, string username)
    {{
        Directory.CreateDirectory(Path.GetDirectoryName(path));
        File.WriteAllText(path, (connected ? "1\\n" : "0\\n") + (username ?? ""));
    }}

    public static void SaveCookies(CoreWebView2 core, string cookieFile, Action done)
    {{
        if (core == null)
        {{
            if (done != null) done();
            return;
        }}
        string[] urls = new string[] {{
            "https://poki.com/",
            "https://www.poki.com/",
            "https://user-vault.poki.com/",
            "https://api.poki.com/",
            "https://games.poki.com/"
        }};
        SaveCookiesFrom(core, cookieFile, urls, 0, new Dictionary<string, string>(), done);
    }}

    public static void ImportCookies(CoreWebView2 core, string cookieFile)
    {{
        try
        {{
            if (core == null || !File.Exists(cookieFile))
                return;
            string[] lines = File.ReadAllLines(cookieFile);
            for (int i = 0; i < lines.Length; i++)
            {{
                try
                {{
                    string line = lines[i].Trim();
                    if (line.Length == 0)
                        continue;
                    string[] parts = line.Split('\t');
                    if (parts.Length < 8)
                        continue;
                    string name = parts[0];
                    string domain = parts[1];
                    string path = string.IsNullOrEmpty(parts[2]) ? "/" : parts[2];
                    if (string.IsNullOrEmpty(name) || string.IsNullOrEmpty(domain))
                        continue;
                    if (domain.IndexOf("poki", StringComparison.OrdinalIgnoreCase) < 0
                        && domain.IndexOf("google", StringComparison.OrdinalIgnoreCase) < 0
                        && domain.IndexOf("firebase", StringComparison.OrdinalIgnoreCase) < 0
                        && domain.IndexOf("apple", StringComparison.OrdinalIgnoreCase) < 0
                        && domain.IndexOf("microsoft", StringComparison.OrdinalIgnoreCase) < 0
                        && domain.IndexOf("live.com", StringComparison.OrdinalIgnoreCase) < 0)
                        continue;
                    string value = Encoding.UTF8.GetString(Convert.FromBase64String(parts[7]));
                    CoreWebView2Cookie cookie = core.CookieManager.CreateCookie(name, value, domain, path);
                    cookie.IsHttpOnly = parts[3] == "1";
                    cookie.IsSecure = parts[4] == "1" || name.StartsWith("__Secure") || name.StartsWith("__Host");
                    cookie.SameSite = cookie.IsSecure
                        ? CoreWebView2CookieSameSiteKind.None
                        : CoreWebView2CookieSameSiteKind.Lax;
                    double expires = 0;
                    double.TryParse(parts[6], System.Globalization.NumberStyles.Float, System.Globalization.CultureInfo.InvariantCulture, out expires);
                    if (parts[5] != "1" && expires > 0)
                        cookie.Expires = new DateTime(1970, 1, 1, 0, 0, 0, DateTimeKind.Utc).AddSeconds(expires).ToLocalTime();
                    core.CookieManager.AddOrUpdateCookie(cookie);
                }}
                catch {{ }}
            }}
        }}
        catch {{ }}
    }}

    static void AppendCookie(Dictionary<string, string> seen, CoreWebView2Cookie cookie)
    {{
        string host = cookie.Domain == null ? "" : cookie.Domain.ToLowerInvariant();
        if (host.IndexOf("poki") < 0 && host.IndexOf("google") < 0 && host.IndexOf("firebase") < 0)
            return;
        string key = cookie.Name + "\\n" + cookie.Domain + "\\n" + cookie.Path;
        string value = Convert.ToBase64String(Encoding.UTF8.GetBytes(cookie.Value ?? ""));
        bool session = cookie.Expires.Year < 2000;
        double unix = 0;
        if (!session)
            unix = (cookie.Expires.ToUniversalTime() - new DateTime(1970, 1, 1, 0, 0, 0, DateTimeKind.Utc)).TotalSeconds;
        seen[key] = cookie.Name + "\\t" + cookie.Domain + "\\t" + cookie.Path + "\\t"
            + (cookie.IsHttpOnly ? "1" : "0") + "\\t" + (cookie.IsSecure ? "1" : "0") + "\\t"
            + (session ? "1" : "0") + "\\t" + unix.ToString(System.Globalization.CultureInfo.InvariantCulture)
            + "\\t" + value + "\\r\\n";
    }}

    static void SaveCookiesFrom(CoreWebView2 core, string cookieFile, string[] urls, int index, Dictionary<string, string> seen, Action done)
    {{
        if (index >= urls.Length)
        {{
            try
            {{
                StringBuilder sb = new StringBuilder();
                foreach (string line in seen.Values)
                    sb.Append(line);
                Directory.CreateDirectory(Path.GetDirectoryName(cookieFile));
                File.WriteAllText(cookieFile, sb.ToString());
            }}
            catch {{ }}
            if (done != null) done();
            return;
        }}
        core.CookieManager.GetCookiesAsync(urls[index]).ContinueWith(
            delegate(Task<List<CoreWebView2Cookie>> task)
            {{
                try
                {{
                    if (task.Status == TaskStatus.RanToCompletion)
                    {{
                        foreach (CoreWebView2Cookie cookie in task.Result)
                            AppendCookie(seen, cookie);
                    }}
                }}
                catch {{ }}
                SaveCookiesFrom(core, cookieFile, urls, index + 1, seen, done);
            }});
    }}
}}

internal sealed class LoginForm : Form
{{
    WebView2 web;
    Label status;
    string userData = {user_data};
    string cookieFile = {cookies_path};
    string accountFile = {account_path};
    string detectedName = "";
    bool sawLogin = false;
    bool closing = false;
    bool autoSaved = false;
    int loginHits = 0;

    public LoginForm()
    {{
        Text = "Connect Poki account";
        Width = 1100;
        Height = 760;
        MinimumSize = new Size(800, 560);
        StartPosition = FormStartPosition.CenterScreen;
        BackColor = Color.FromArgb(15, 17, 23);
        try
        {{
            if (File.Exists({icon_path}))
                Icon = new Icon({icon_path});
        }}
        catch {{ }}

        Panel bar = new Panel();
        bar.Dock = DockStyle.Top;
        bar.Height = 64;
        bar.BackColor = Color.FromArgb(22, 25, 34);

        status = new Label();
        status.Text = "Sign in to Poki with Google, Apple, Microsoft, or a passkey. Already signed in? This window will detect it.";
        status.ForeColor = Color.FromArgb(232, 234, 237);
        status.Font = new Font("Segoe UI", 10f);
        status.AutoSize = false;
        status.SetBounds(16, 8, 760, 48);

        Button done = new Button();
        done.Text = "Done";
        done.Width = 110;
        done.Height = 36;
        done.Anchor = AnchorStyles.Top | AnchorStyles.Right;
        done.BackColor = Color.FromArgb(124, 92, 255);
        done.ForeColor = Color.White;
        done.FlatStyle = FlatStyle.Flat;
        done.FlatAppearance.BorderSize = 0;
        done.Font = new Font("Segoe UI", 10f, FontStyle.Bold);
        done.Click += delegate {{ Finish(true); }};
        bar.Resize += delegate {{ done.Left = bar.Width - done.Width - 16; done.Top = 14; }};

        bar.Controls.Add(status);
        bar.Controls.Add(done);
        Controls.Add(bar);

        web = new WebView2();
        web.Dock = DockStyle.Fill;
        web.DefaultBackgroundColor = Color.FromArgb(15, 17, 23);
        web.CreationProperties = new CoreWebView2CreationProperties();
        web.CreationProperties.UserDataFolder = userData;
        web.CreationProperties.AdditionalBrowserArguments =
            "--disable-features=ThirdPartyStoragePartitioning,TrackingPrevention,msWebView2EnableTrackingPrevention";
        Controls.Add(web);
        web.BringToFront();

        Load += delegate {{ web.EnsureCoreWebView2Async(null); }};
        web.CoreWebView2InitializationCompleted += OnReady;
        FormClosing += delegate(object sender, FormClosingEventArgs e)
        {{
            if (closing)
                return;
            e.Cancel = true;
            Finish(false);
        }};
    }}

    void OnReady(object sender, CoreWebView2InitializationCompletedEventArgs e)
    {{
        if (!e.IsSuccess)
        {{
            MessageBox.Show("Microsoft Edge WebView2 is required to sign in to Poki.", "PokiWrap");
            closing = true;
            Close();
            return;
        }}
        web.CoreWebView2.Settings.IsZoomControlEnabled = false;
        web.CoreWebView2.Settings.IsStatusBarEnabled = false;
        web.CoreWebView2.Settings.IsWebMessageEnabled = true;
        web.CoreWebView2.Settings.UserAgent =
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0";
        web.CoreWebView2.PermissionRequested += delegate(object sPerm, CoreWebView2PermissionRequestedEventArgs ePerm)
        {{
            ePerm.Handled = true;
            ePerm.State = CoreWebView2PermissionState.Allow;
        }};
        web.CoreWebView2.NewWindowRequested += delegate(object sWin, CoreWebView2NewWindowRequestedEventArgs eWin)
        {{
            eWin.Handled = true;
            web.CoreWebView2.Navigate(eWin.Uri);
        }};
        web.CoreWebView2.WebMessageReceived += delegate(object sMsg, CoreWebView2WebMessageReceivedEventArgs eMsg)
        {{
            string msg = "";
            try {{ msg = eMsg.TryGetWebMessageAsString(); }} catch {{ }}
            if (msg.IndexOf("\\"loggedIn\\":true") >= 0)
            {{
                string user = "";
                int key = msg.IndexOf("\\"username\\":\\"");
                if (key >= 0)
                {{
                    int start = key + 13;
                    int end = msg.IndexOf("\\"", start);
                    if (end > start)
                        user = msg.Substring(start, end - start);
                }}
                MarkLoggedIn(user);
            }}
        }};
        web.CoreWebView2.AddScriptToExecuteOnDocumentCreatedAsync({detect_js});
        AccountStore.ImportCookies(web.CoreWebView2, cookieFile);
        web.CoreWebView2.Navigate("https://poki.com/en");
        Timer persist = new Timer();
        persist.Interval = 1500;
        persist.Tick += delegate
        {{
            try {{ AccountStore.SaveCookies(web.CoreWebView2, cookieFile, null); }} catch {{ }}
            try
            {{
                web.CoreWebView2.CookieManager.GetCookiesAsync("https://user-vault.poki.com/").ContinueWith(
                    delegate(Task<List<CoreWebView2Cookie>> task)
                    {{
                        try
                        {{
                            if (task.Status != TaskStatus.RanToCompletion || task.Result == null)
                                return;
                            bool auth = false;
                            foreach (CoreWebView2Cookie cookie in task.Result)
                            {{
                                string n = cookie.Name == null ? "" : cookie.Name.ToLowerInvariant();
                                if (n.IndexOf("optanon") >= 0 || n.IndexOf("_ga") >= 0 || n == "cf_clearance")
                                    continue;
                                if (n.IndexOf("session") >= 0 || n.IndexOf("token") >= 0 || n.IndexOf("auth") >= 0
                                    || n.IndexOf("vault") >= 0 || n.IndexOf("user") >= 0 || n.IndexOf("sid") >= 0
                                    || n.IndexOf("poki") >= 0)
                                    auth = true;
                            }}
                            if (!auth)
                                return;
                            BeginInvoke(new Action(delegate {{ MarkLoggedIn(detectedName); }}));
                        }}
                        catch {{ }}
                    }});
            }}
            catch {{ }}
        }};
        persist.Start();
    }}

    void MarkLoggedIn(string username)
    {{
        if (closing)
            return;
        if (!string.IsNullOrEmpty(username))
            detectedName = username;
        sawLogin = true;
        loginHits++;
        status.Text = string.IsNullOrEmpty(detectedName)
            ? "Signed in. Saving this account to PokiWrap..."
            : ("Signed in as " + detectedName + ". Saving...");
        if (autoSaved || loginHits < 2)
            return;
        autoSaved = true;
        Timer done = new Timer();
        done.Interval = 400;
        done.Tick += delegate
        {{
            done.Stop();
            Finish(true);
        }};
        done.Start();
    }}

    void Finish(bool signedIn)
    {{
        if (closing)
            return;
        closing = true;
        CoreWebView2 core = null;
        try {{ core = web.CoreWebView2; }} catch {{ }}
        AccountStore.SaveCookies(core, cookieFile, delegate
        {{
            try
            {{
                bool connected = signedIn || sawLogin || !string.IsNullOrEmpty(detectedName);
                AccountStore.WriteAccount(accountFile, connected, detectedName);
                if (!connected)
                {{
                    try {{ File.Delete(cookieFile); }} catch {{ }}
                }}
            }}
            catch {{ }}
            BeginInvoke(new Action(Close));
        }});
    }}
}}

internal sealed class SignOutForm : Form
{{
    public SignOutForm()
    {{
        Width = 1;
        Height = 1;
        ShowInTaskbar = false;
        Opacity = 0;
        WebView2 web = new WebView2();
        web.CreationProperties = new CoreWebView2CreationProperties();
        web.CreationProperties.UserDataFolder = {user_data};
        Controls.Add(web);
        Load += delegate {{ web.EnsureCoreWebView2Async(null); }};
        web.CoreWebView2InitializationCompleted += delegate(object sender, CoreWebView2InitializationCompletedEventArgs e)
        {{
            try
            {{
                if (e.IsSuccess)
                    web.CoreWebView2.CookieManager.DeleteAllCookies();
            }}
            catch {{ }}
            try {{ File.Delete({cookies_path}); }} catch {{ }}
            AccountStore.WriteAccount({account_path}, false, "");
            Close();
        }};
    }}
}}
"""


def _compile_webview_exe(source_path: Path, exe_path: Path, icon: Path | None) -> None:
    csc = _csc_path()
    if csc is None:
        raise RuntimeError("The .NET C# compiler was not found.")
    webview = ensure_webview2()
    core = webview / "Microsoft.Web.WebView2.Core.dll"
    winforms = webview / "Microsoft.Web.WebView2.WinForms.dll"
    command = [
        str(csc),
        "/nologo",
        "/optimize+",
        "/target:winexe",
        "/platform:x64",
        "/r:System.Windows.Forms.dll",
        "/r:System.Drawing.dll",
        f"/r:{core}",
        f"/r:{winforms}",
        f"/out:{exe_path}",
        str(source_path),
        str(_adblock_source()),
    ]
    if icon is not None and icon.exists():
        command.insert(command.index(str(source_path)), f"/win32icon:{icon}")
    completed = subprocess.run(command, capture_output=True, text=True)
    if completed.returncode != 0 and icon is not None and icon.exists():
        command = [arg for arg in command if not arg.startswith("/win32icon:")]
        completed = subprocess.run(command, capture_output=True, text=True)
    try:
        source_path.unlink(missing_ok=True)
    except OSError:
        pass
    if completed.returncode != 0 or not exe_path.exists():
        raise RuntimeError(
            completed.stderr.strip()
            or completed.stdout.strip()
            or "Failed to compile the native .exe."
        )


def build_login_exe() -> Path:
    webview = ensure_webview2()
    exe_path = runtime_dir() / "PokiAccount.exe"
    source_path = runtime_dir() / "_login.cs"
    icon = assets_dir() / "pokiwrap.ico"
    source_path.write_text(
        LOGIN_CS.format(
            runtime=_csharp_string(str(webview.resolve())),
            icon_path=_csharp_string(str(icon.resolve()) if icon.exists() else ""),
            user_data=_csharp_string(str(account_profile_dir().resolve())),
            cookies_path=_csharp_string(str(account_cookies_path())),
            account_path=_csharp_string(str(account_state_path())),
            detect_js=_csharp_string(DETECT_JS),
            adblock_list=_csharp_string(str(adblock_domains_path())),
            adblock_settings=_csharp_string(str(settings_path())),
        ),
        encoding="utf-8",
    )
    _compile_webview_exe(source_path, exe_path, icon if icon.exists() else None)
    return exe_path


def ensure_login_exe() -> Path:
    return build_login_exe()


def _package_macos_release(app_path: Path, root: Path) -> Path:
    """Sign the .app, zip with ditto (keeps symlinks), and add a Gatekeeper opener."""
    stage = app_path.parent / "macos_release"
    if stage.exists():
        shutil.rmtree(stage)
    stage.mkdir(parents=True)
    staged_app = stage / "PokiWrap.app"
    shutil.copytree(app_path, staged_app, symlinks=True)
    subprocess.run(["xattr", "-cr", str(staged_app)], check=False)
    info_path = staged_app / "Contents" / "Info.plist"
    if info_path.exists():
        import plistlib

        with info_path.open("rb") as handle:
            info = plistlib.load(handle)
        info["NSHighResolutionCapable"] = True
        info["NSAppTransportSecurity"] = {"NSAllowsArbitraryLoads": True}
        with info_path.open("wb") as handle:
            plistlib.dump(info, handle)
    entitlements = root / "packaging" / "macos.entitlements"
    sign_cmd = ["codesign", "--force", "--sign", "-", "--timestamp=none"]
    if entitlements.exists():
        sign_cmd.extend(["--entitlements", str(entitlements)])
    main_bin = staged_app / "Contents" / "MacOS" / "PokiWrap"
    if main_bin.exists():
        subprocess.run(sign_cmd + [str(main_bin)], check=False)
    signed = subprocess.run(
        sign_cmd + [str(staged_app)],
        capture_output=True,
        text=True,
    )
    if signed.returncode != 0:
        raise RuntimeError(signed.stderr[-2000:] if signed.stderr else "codesign failed.")
    opener = stage / "Open PokiWrap.command"
    opener.write_text(
        "#!/bin/bash\n"
        'DIR="$(cd "$(dirname "$0")" && pwd)"\n'
        'APP="$DIR/PokiWrap.app"\n'
        'xattr -cr "$APP" 2>/dev/null || true\n'
        'BIN="$APP/Contents/MacOS/PokiWrap"\n'
        'if [ -x "$BIN" ]; then exec "$BIN"; fi\n'
        'open "$APP"\n',
        encoding="utf-8",
        newline="\n",
    )
    opener.chmod(0o755)
    zip_path = root / "PokiWrap-mac.zip"
    if zip_path.exists():
        zip_path.unlink()
    ditto = subprocess.run(
        ["ditto", "-c", "-k", str(stage), str(zip_path)],
        capture_output=True,
        text=True,
    )
    if ditto.returncode != 0 or not zip_path.exists():
        raise RuntimeError(ditto.stderr[-2000:] if ditto.stderr else "ditto zip failed.")
    release = root / "web" / "public" / "downloads" / "PokiWrap-mac.zip"
    try:
        release.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(zip_path, release)
    except OSError:
        pass
    return zip_path


def build_pokiwrap_exe() -> Path | None:
    """Freeze the generator UI for the current OS (Windows .exe or macOS .app)."""
    from pokiwrap.paths import assets_dir, project_root

    if sys.platform not in {"win32", "darwin"}:
        return None

    icon = assets_dir() / "pokiwrap.ico"
    dist = runtime_dir() / "pokiwrap_dist"
    work = runtime_dir() / "pokiwrap_build"
    python = python_executable().replace("pythonw.exe", "python.exe")
    command = [
        python,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--windowed",
        "--name",
        "PokiWrap",
        "--distpath",
        str(dist),
        "--workpath",
        str(work),
        "--specpath",
        str(work),
        "--hidden-import",
        "pokiwrap",
        "--collect-submodules",
        "pokiwrap",
        "--hidden-import",
        "PyQt6.QtWidgets",
        "--hidden-import",
        "PyQt6.QtGui",
        "--hidden-import",
        "PyQt6.QtCore",
        "--collect-binaries",
        "PyQt6",
        "--hidden-import",
        "cryptography",
        "--hidden-import",
        "cffi",
        "--collect-binaries",
        "cryptography",
        "--add-data",
        str(project_root() / "pokiwrap" / "engine" / "adblock_host.cs") + os.pathsep + "pokiwrap/engine",
        "--add-data",
        str(project_root() / "assets") + os.pathsep + "assets",
        str(project_root() / "main.py"),
    ]
    command.extend(
        [
            "--collect-data",
            "certifi",
            "--hidden-import",
            "certifi",
        ]
    )
    if sys.platform == "win32":
        command.insert(command.index("--windowed") + 1, "--onefile")
        command.extend(
            [
                "--exclude-module",
                "PyQt6.QtWebEngineCore",
                "--exclude-module",
                "PyQt6.QtWebEngineWidgets",
                "--exclude-module",
                "PyQt6.QtWebEngineQuick",
            ]
        )
    else:
        entitlements = project_root() / "packaging" / "macos.entitlements"
        command.extend(
            [
                "--osx-bundle-identifier",
                "app.pokiwrap.desktop",
                "--codesign-identity",
                "-",
                "--hidden-import",
                "PyQt6.QtWebEngineWidgets",
                "--hidden-import",
                "PyQt6.QtWebEngineCore",
                "--collect-submodules",
                "PyQt6.QtWebEngineCore",
                "--collect-submodules",
                "PyQt6.QtWebEngineWidgets",
            ]
        )
        if entitlements.exists():
            command.extend(["--osx-entitlements-file", str(entitlements)])
    if icon.exists():
        icon_path = icon
        if sys.platform == "darwin":
            icns = runtime_dir() / "pokiwrap.icns"
            icns.parent.mkdir(parents=True, exist_ok=True)
            try:
                from PIL import Image

                image = Image.open(icon)
                image.save(icns, format="ICNS")
                icon_path = icns
            except Exception:
                icon_path = None
        if icon_path:
            command.extend(["--icon", str(icon_path)])
    completed = subprocess.run(command, capture_output=True, text=True, cwd=str(project_root()))
    if sys.platform == "win32":
        exe = dist / "PokiWrap.exe"
        onedir = dist / "PokiWrap" / "PokiWrap.exe"
        built = exe if exe.exists() else onedir
        if completed.returncode != 0 or not built.exists():
            raise RuntimeError(completed.stderr[-2000:] if completed.stderr else "PyInstaller failed.")
        dest = project_root() / "PokiWrap.exe"
        if built.resolve() != dest.resolve():
            shutil.copy2(built, dest)
        desktop_copy = desktop_dir() / "PokiWrap.exe"
        try:
            shutil.copy2(dest, desktop_copy)
        except OSError:
            pass
        release = project_root() / "web" / "public" / "downloads" / "PokiWrap-windows.exe"
        try:
            release.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(dest, release)
        except OSError:
            pass
        return dest

    app_path = dist / "PokiWrap.app"
    if completed.returncode != 0 or not app_path.exists():
        raise RuntimeError(completed.stderr[-2000:] if completed.stderr else "PyInstaller failed.")
    return _package_macos_release(app_path, project_root())


def build_pokiwrap_app() -> Path | None:
    return build_pokiwrap_exe()
