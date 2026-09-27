// <baobab-nav> — the frame's bar, mounted on the frame's pages and on any frond
// that sets NAV_SRC to this file (CONTRACT.md section 6).
//
//   <script src="https://frame.example/static/embed/nav.js" defer></script>
//   <baobab-nav></baobab-nav>
//
// It reads from the frame that served the script; data-up names another.
//
// Its places come from the frame (GET <data-up>/api/nav/), filtered there for the
// person looking. No hostname is built here. Signed out: the site name and
// "Sign in". Quiet failure: if the frame does not answer, the bar shows nothing.
// Vanilla JS, no shadow DOM, textContent-only writes. Restyle from the host page
// with `baobab-nav .bn-bar`, `baobab-nav a`, `baobab-nav a[aria-current="page"]`.

(function () {
  'use strict';
  if (window.customElements && customElements.get('baobab-nav')) return;

  // The frame that served this file; data-up overrides it.
  var FRAME = document.currentScript ? new URL(document.currentScript.src).origin : '';

  function ensureStyles() {
    if (document.getElementById('baobab-nav-styles')) return;
    var s = document.createElement('style');
    s.id = 'baobab-nav-styles';
    s.textContent = [
      'baobab-nav { display: block; min-height: 40px; background: var(--bb-surface, #fffefb); border-bottom: 1px solid var(--bb-border, #e6e1d8); font: 13px/1 var(--bb-font-body, system-ui, sans-serif); }',
      'baobab-nav .bn-bar { display: flex; align-items: center; gap: 2px; height: 40px; padding: 0 12px; }',
      'baobab-nav .bn-places { flex: 1; min-width: 0; display: flex; gap: 2px; overflow-x: auto; scrollbar-width: none; }',
      'baobab-nav .bn-places::-webkit-scrollbar { display: none; }',
      'baobab-nav .bn-site, baobab-nav .bn-account { flex: none; }',
      'baobab-nav .bn-me { max-width: 12em; overflow: hidden; text-overflow: ellipsis; }',
      'baobab-nav a { color: var(--bb-ink-2, #5d574d); text-decoration: none; padding: 6px 10px; border-radius: 6px; white-space: nowrap; }',
      'baobab-nav a:hover { color: var(--bb-ink, #26221c); background: rgba(127,127,127,0.1); }',
      'baobab-nav a[aria-current="page"] { color: var(--bb-ink, #26221c); font-weight: 600; }',
      'baobab-nav .bn-site { font-weight: 650; color: var(--bb-ink, #26221c); padding-left: 0; }',
      'baobab-nav .bn-account { position: relative; }',
      'baobab-nav .bn-me { font: inherit; color: var(--bb-ink-2, #5d574d); background: none; border: 0; padding: 6px 10px; border-radius: 6px; cursor: pointer; white-space: nowrap; }',
      'baobab-nav .bn-me:hover { background: rgba(127,127,127,0.1); }',
      'baobab-nav .bn-menu { position: fixed; right: 12px; top: 40px; z-index: 50; min-width: 9rem; padding: 4px 0; background: var(--bb-surface, #fffefb); border: 1px solid var(--bb-border, #e6e1d8); border-radius: 8px; box-shadow: 0 6px 20px rgba(0,0,0,0.08); }',
      'baobab-nav .bn-menu[hidden] { display: none; }',
      'baobab-nav .bn-menu button { display: block; width: 100%; text-align: left; font: inherit; color: var(--bb-ink, #26221c); background: none; border: 0; padding: 8px 12px; cursor: pointer; }',
      'baobab-nav .bn-menu button:hover { background: rgba(127,127,127,0.1); }',
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

  class BaobabNav extends HTMLElement {
    connectedCallback() {
      if (this._started) return;
      this._started = true;
      ensureStyles();
      var up = this.up = (this.dataset.up || FRAME).replace(/\/$/, '');
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
        // The frame's front page carries its own Sign in; say it once.
        bar.appendChild(link(nav.login_url + '?next=' + encodeURIComponent(location.href), 'Sign in'));
      }
      this.textContent = '';
      this.appendChild(bar);
    }

    // The person's name opens a menu with Sign out. Signing out ends the session on
    // this frame and lands on its front page; the sign-in provider keeps its own
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
        fetch(up + '/api/logout/', { method: 'POST', credentials: 'include', headers: { 'X-Baobab': '1' } })
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

  customElements.define('baobab-nav', BaobabNav);
})();
