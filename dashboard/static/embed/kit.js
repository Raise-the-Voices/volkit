// Helpers for this app's web components. The generator copied this file in; it is not
// shared with any other app. The web components file loads it from the same directory
// and finds it at window.embedKits[<this file's URL>], so two apps' kits on one
// dashboard never replace each other.
//
// Every call takes the card element (`host`) and reads its data-up.

(function () {
  'use strict';

  var HERE = document.currentScript.src;

  function embedKit(slug) {
    function up(host) {
      var base = (host.dataset.up || '').replace(/\/+$/, '');
      if (!base) throw new Error(host.tagName.toLowerCase() + ' has no data-up');
      return base;
    }

    // GET JSON with the viewer's own session. Rejects on anything but a 200.
    function getJSON(host, path) {
      return Promise.resolve()
        .then(function () { return fetch(up(host) + path, { credentials: 'include' }); })
        .then(function (response) {
          if (response.status !== 200) throw new Error('http ' + response.status);
          return response.json();
        });
    }

    function post(host, path, body) {
      return Promise.resolve()
        .then(function () {
          return fetch(up(host) + path, {
            method: 'POST',
            credentials: 'include',
            headers: { 'Content-Type': 'application/json', 'X-Embed': '1' },
            body: JSON.stringify(body),
          });
        })
        .then(function (response) {
          if (!response.ok) throw new Error('http ' + response.status);
          return response.status === 204 ? null : response.json();
        });
    }

    function hide(host) {
      host.replaceChildren();
      host.hidden = true;
    }

    function changed(type, id) {
      document.dispatchEvent(new CustomEvent(slug + ':changed', { detail: { type: type, id: id } }));
    }

    return { getJSON: getJSON, post: post, hide: hide, changed: changed };
  }

  (window.embedKits = window.embedKits || {})[HERE] = embedKit;
})();
