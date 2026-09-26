// VolKit cards. Vanilla custom elements: no framework, no build step, no shadow
// DOM. Style them from the host page by tag name. Each hides itself when it has
// nothing to show.
//
//   <volkit-team-articles data-up="<VolKit>" data-org="<org>">
//     The newest published articles (max 4), each a link to read and share.
//   <volkit-my-articles data-up="<VolKit>" data-org="<org>">
//     The signed-in person's own articles, drafts included, each a link to edit.

(function () {
  'use strict';

  var SLUG = 'volkit';
  var KIT = new URL('kit.js', document.currentScript.src).href;

  function loadKit() {
    return new Promise(function (resolve, reject) {
      var script = document.createElement('script');
      script.src = KIT;
      script.onload = function () { resolve(window.baobabKits[KIT](SLUG)); };
      script.onerror = reject;
      document.head.appendChild(script);
    });
  }

  function safeUrl(url) {
    return typeof url === 'string' && /^https?:\/\//i.test(url);
  }

  // A list card: GET <path>, one row per item from row(item), hide when empty.
  function defineList(kit, tag, path, row) {
    if (customElements.get(tag)) return;
    customElements.define(tag, class extends HTMLElement {
      connectedCallback() {
        var host = this;
        var org = host.dataset.org;
        if (!org) return kit.hide(host);
        kit.getJSON(host, '/api/orgs/' + encodeURIComponent(org) + path).then(function (items) {
          if (!Array.isArray(items)) return kit.hide(host);
          var list = document.createElement('ul');
          items.forEach(function (item) {
            var li = row(item);
            if (li) list.appendChild(li);
          });
          if (!list.children.length) return kit.hide(host);
          host.replaceChildren(list);
          host.hidden = false;
        }).catch(function () { kit.hide(host); });
      }
    });
  }

  function link(text, href) {
    var a = document.createElement('a');
    a.textContent = text;
    a.href = href;
    return a;
  }

  function define(kit) {
    defineList(kit, 'volkit-team-articles', '/articles/team/', function (post) {
      if (!safeUrl(post.url)) return null;
      var li = document.createElement('li');
      li.appendChild(link(post.title, post.url));
      return li;
    });
    defineList(kit, 'volkit-my-articles', '/articles/mine/', function (post) {
      if (!safeUrl(post.edit_url)) return null;
      var li = document.createElement('li');
      li.appendChild(link(post.title || '(untitled)', post.edit_url));
      var status = document.createElement('small');
      status.textContent = ' ' + post.status;
      li.appendChild(status);
      return li;
    });
  }

  loadKit().then(define, function () {
    document.querySelectorAll('volkit-team-articles, volkit-my-articles')
      .forEach(function (card) { card.hidden = true; });
  });
})();
