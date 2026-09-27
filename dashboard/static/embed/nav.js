// <site-nav>: the dashboard app's nav bar, mounted on its pages and on any other app
// that loads this file, so every place looks like one (CONTRACT.md section 6).
//
//   <script src="https://dashboard.example/static/embed/nav.js" defer></script>
//   <site-nav></site-nav>
//
// It reads from the dashboard app that served the script; data-up names another.
//
// Its places come from the dashboard app (GET <data-up>/api/nav/), shown to anyone signed in. No hostname is built here. Signed out: the site name and
// "Sign in". Quiet failure: if the dashboard app does not answer, the bar shows nothing.
// Vanilla JS, no shadow DOM, textContent-only writes. Restyle from the host page
// with `site-nav .bn-bar`, `site-nav a`, `site-nav a[aria-current="page"]`.

(function () {
  'use strict';
  if (window.customElements && customElements.get('site-nav')) return;

  // The dashboard app that served this file; data-up overrides it.
  var ORIGIN = document.currentScript ? new URL(document.currentScript.src).origin : '';

  function ensureStyles() {
    if (document.getElementById('site-nav-styles')) return;
    var s = document.createElement('style');
    s.id = 'site-nav-styles';
    s.textContent = [
      'site-nav { display: block; min-height: 40px; background: var(--theme-surface, #fffefb); border-bottom: 1px solid var(--theme-border, #e6e1d8); font: 13px/1 var(--theme-font-body, system-ui, sans-serif); }',
      'site-nav .bn-bar { display: flex; align-items: center; gap: 2px; height: 40px; padding: 0 12px; }',
      'site-nav .bn-places { flex: 1; min-width: 0; display: flex; gap: 2px; overflow-x: auto; scrollbar-width: none; }',
      'site-nav .bn-places::-webkit-scrollbar { display: none; }',
      'site-nav .bn-site, site-nav .bn-account { flex: none; }',
      'site-nav .bn-me { max-width: 12em; overflow: hidden; text-overflow: ellipsis; }',
      'site-nav a { color: var(--theme-ink-2, #5d574d); text-decoration: none; padding: 6px 10px; border-radius: 6px; white-space: nowrap; }',
      'site-nav a:hover { color: var(--theme-ink, #26221c); background: rgba(127,127,127,0.1); }',
      'site-nav a[aria-current="page"] { color: var(--theme-ink, #26221c); font-weight: 600; }',
      'site-nav .bn-site { font-weight: 650; color: var(--theme-ink, #26221c); padding-left: 0; }',
      'site-nav .bn-account { position: relative; }',
      'site-nav .bn-me { font: inherit; color: var(--theme-ink-2, #5d574d); background: none; border: 0; padding: 6px 10px; border-radius: 6px; cursor: pointer; white-space: nowrap; }',
      'site-nav .bn-me:hover { background: rgba(127,127,127,0.1); }',
      'site-nav .bn-menu { position: fixed; right: 12px; top: 40px; z-index: 50; min-width: 9rem; padding: 4px 0; background: var(--theme-surface, #fffefb); border: 1px solid var(--theme-border, #e6e1d8); border-radius: 8px; box-shadow: 0 6px 20px rgba(0,0,0,0.08); }',
      'site-nav .bn-menu[hidden] { display: none; }',
      'site-nav .bn-menu button { display: block; width: 100%; text-align: left; font: inherit; color: var(--theme-ink, #26221c); background: none; border: 0; padding: 8px 12px; cursor: pointer; }',
      'site-nav .bn-menu button:hover { background: rgba(127,127,127,0.1); }',
    ].join('\n');
    document.head.appendChild(s);
  }

  function link(href, text, cls) {
    var a = document.createElement('a');
    a.href = href;
    a.textContent = text;
    if (cls) a.className = cls;
    return a;
  }

  function isHere(href) {
    try {
      var u = new URL(href, location.href);
      var want = u.pathname.replace(/\/+$/, '');
      var here = location.pathname.replace(/\/+$/, '');
      return u.origin === location.origin && want !== '' && (here === want || here.indexOf(want + '/') === 0);
    } catch (e) { return false; }
  }

  class SiteNav extends HTMLElement {
    connectedCallback() {
      if (this._started) return;
      this._started = true;
      ensureStyles();
      var up = this.up = (this.dataset.up || ORIGIN).replace(/\/$/, '');
      var self = this;
      if (!up) return;
      fetch(up + '/api/nav/', { credentials: 'include' })
        .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
        .then(function (nav) { self.render(nav); })
        .catch(function () {});
    }

    render(nav) {
      var bar = document.createElement('nav');
      bar.className = 'bn-bar';
      bar.setAttribute('aria-label', nav.site.name);
      bar.appendChild(link(nav.site.url, nav.site.name, 'bn-site'));
      // The places scroll sideways on a narrow screen; the site name and the account stay put.
      var places = document.createElement('span');
      places.className = 'bn-places';
      (nav.places || []).forEach(function (p) {
        var a = link(p.url, p.label);
        if (isHere(p.url)) a.setAttribute('aria-current', 'page');
        places.appendChild(a);
      });
      bar.appendChild(places);
      if (nav.me) {
        bar.appendChild(this.account(nav.me.name, nav.site.url));
      } else if (location.href !== nav.site.url) {
        // The dashboard app's front page carries its own Sign in; say it once.
        bar.appendChild(link(nav.login_url + '?next=' + encodeURIComponent(location.href), 'Sign in'));
      }
      this.textContent = '';
      this.appendChild(bar);
    }

    // The person's name opens a menu with Sign out. Signing out ends the session on
    // this dashboard app and lands on its front page; the sign-in provider keeps its own
    // session, so signing back in is one click.
    account(name, home) {
      var up = this.up;
      var wrap = document.createElement('span');
      wrap.className = 'bn-account';
      var toggle = document.createElement('button');
      toggle.type = 'button';
      toggle.className = 'bn-me';
      toggle.textContent = name;
      toggle.setAttribute('aria-haspopup', 'true');
      toggle.setAttribute('aria-expanded', 'false');
      var menu = document.createElement('div');
      menu.className = 'bn-menu';
      menu.hidden = true;
      var out = document.createElement('button');
      out.type = 'button';
      out.textContent = 'Sign out';
      out.addEventListener('click', function () {
        fetch(up + '/api/logout/', { method: 'POST', credentials: 'include', headers: { 'X-Embed': '1' } })
          .then(function () { location.assign(home); });
      });
      menu.appendChild(out);
      toggle.addEventListener('click', function (e) {
        e.stopPropagation();
        menu.hidden = !menu.hidden;
        toggle.setAttribute('aria-expanded', String(!menu.hidden));
      });
      document.addEventListener('click', function () {
        menu.hidden = true;
        toggle.setAttribute('aria-expanded', 'false');
      });
      wrap.append(toggle, menu);
      return wrap;
    }
  }

  customElements.define('site-nav', SiteNav);
})();
