using System;
using System.Collections.Generic;
using System.IO;
using Microsoft.Web.WebView2.Core;

internal static class AdBlock
{
    static HashSet<string> blocked;
    static bool enabled = true;
    static bool loaded;

    public static void Attach(CoreWebView2 core, string listFile, string settingsFile)
    {
        if (core == null)
            return;
        Load(listFile, settingsFile);
        if (!enabled)
            return;
        try
        {
            core.AddWebResourceRequestedFilter("*", CoreWebView2WebResourceContext.All);
            core.WebResourceRequested += OnRequest;
        }
        catch { }
    }

    static void Load(string listFile, string settingsFile)
    {
        if (loaded)
            return;
        loaded = true;
        blocked = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        try
        {
            if (File.Exists(settingsFile))
            {
                string text = File.ReadAllText(settingsFile);
                if (text.IndexOf("\"adblock\": false") >= 0 || text.IndexOf("\"adblock\":false") >= 0)
                    enabled = false;
            }
        }
        catch { }
        if (!enabled)
            return;
        string[] seed = new string[] {
            "ads.poki.com", "doubleclick.net", "googleadservices.com", "googlesyndication.com",
            "googletagmanager.com", "google-analytics.com", "imasdk.googleapis.com",
            "amazon-adsystem.com", "adnxs.com", "adsrvr.org", "criteo.com", "criteo.net",
            "taboola.com", "outbrain.com", "scorecardresearch.com", "2mdn.net", "moatads.com",
            "pagead2.googlesyndication.com", "tpc.googlesyndication.com", "pubmatic.com",
            "rubiconproject.com", "prebid.org", "hotjar.com", "quantserve.com"
        };
        for (int i = 0; i < seed.Length; i++)
            blocked.Add(seed[i]);
        try
        {
            if (File.Exists(listFile))
            {
                string[] lines = File.ReadAllLines(listFile);
                for (int i = 0; i < lines.Length; i++)
                {
                    string line = lines[i].Trim().ToLowerInvariant();
                    if (line.Length > 0 && line[0] != '#')
                        blocked.Add(line);
                }
            }
        }
        catch { }
    }

    static bool Allowed(string host)
    {
        if (host == "ads.poki.com")
            return false;
        if (host == "poki.com" || host == "www.poki.com")
            return true;
        if (host == "games.poki.com" || host.EndsWith(".games.poki.com"))
            return true;
        if (host == "poki-gdn.com" || host.EndsWith(".poki-gdn.com"))
            return true;
        if (host == "poki-cdn.com" || host.EndsWith(".poki-cdn.com"))
            return true;
        if (host == "game-cdn.poki.com" || host == "user-vault.poki.com")
            return true;
        if (host == "api.poki.com" || host.EndsWith(".api.poki.com"))
            return true;
        if (host == "auth.poki.com" || host == "account.poki.com" || host == "accounts.poki.com")
            return true;
        if (host.Contains("firebase"))
            return true;
        if (host == "identitytoolkit.googleapis.com" || host == "securetoken.googleapis.com")
            return true;
        if (host == "firebaseinstallations.googleapis.com" || host == "firestore.googleapis.com")
            return true;
        if (host == "oauth2.googleapis.com" || host == "www.googleapis.com")
            return true;
        if (host == "accounts.google.com" || host == "appleid.apple.com")
            return true;
        if (host == "login.microsoftonline.com" || host == "login.live.com")
            return true;
        if (host == "gstatic.com" || host.EndsWith(".gstatic.com"))
            return true;
        return false;
    }

    static bool ShouldBlock(string uri)
    {
        try
        {
            Uri parsed = new Uri(uri);
            string host = parsed.Host;
            if (string.IsNullOrEmpty(host))
                return false;
            host = host.ToLowerInvariant();
            if (Allowed(host))
                return false;
            string current = host;
            while (true)
            {
                if (blocked != null && blocked.Contains(current))
                    return true;
                int dot = current.IndexOf('.');
                if (dot <= 0)
                    break;
                current = current.Substring(dot + 1);
            }
        }
        catch { }
        return false;
    }

    static void OnRequest(object sender, CoreWebView2WebResourceRequestedEventArgs e)
    {
        try
        {
            if (!ShouldBlock(e.Request.Uri))
                return;
            CoreWebView2 core = sender as CoreWebView2;
            if (core == null || core.Environment == null)
                return;
            e.Response = core.Environment.CreateWebResourceResponse(new MemoryStream(), 204, "No Content", "Content-Type: text/plain");
        }
        catch { }
    }
}
