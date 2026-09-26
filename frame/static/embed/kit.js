// Helpers for this frond's cards. The generator copied this file in; it is not
// shared with any other frond. The cards file loads it from the same directory
// and finds it at window.baobabKits[<this file's URL>], so two fronds' kits on
// one dashboard never replace each other.
//
// Every call takes the card element (`host`) and reads its data-up.

(function () {
  'use strict';

  var HERE = document.currentScript.src;

  function baobabKit(slug) {
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
            headers: { 'Content-Type': 'application/json', 'X-Baobab': '1' },
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

    // Calls onMessage({topic, type, id}) for each message on these topics.
    // Returns a function that stops listening. A backend without live updates
    // just never sends anything.
    function live(host, topics, onMessage) {
      var source;
      try {
        source = new EventSource(
          up(host) + '/api/live/?topics=' + encodeURIComponent(topics.join(',')),
          { withCredentials: true }
        );
      } catch (e) {
        return function () {};
      }
      source.onmessage = function (event) {
        var message;
        try { message = JSON.parse(event.data); } catch (e) { return; }
        if (message && topics.indexOf(message.topic) !== -1) onMessage(message);
      };
      return function () { source.close(); };
    }

    return { getJSON: getJSON, post: post, hide: hide, changed: changed, live: live };
  }

  (window.baobabKits = window.baobabKits || {})[HERE] = baobabKit;
})();
