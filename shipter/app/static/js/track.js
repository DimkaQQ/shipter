(function () {
  var script = document.currentScript;
  if (!script) return;
  var projectId = script.getAttribute('data-project');
  if (!projectId) return;

  var origin = new URL(script.src).origin;
  var payload = JSON.stringify({
    project_id: projectId,
    path: location.pathname,
    referrer: document.referrer || ''
  });

  function send() {
    var url = origin + '/t/collect';
    if (navigator.sendBeacon) {
      var blob = new Blob([payload], { type: 'application/json' });
      navigator.sendBeacon(url, blob);
    } else {
      fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: payload,
        keepalive: true
      }).catch(function () {});
    }
  }

  send();
})();
