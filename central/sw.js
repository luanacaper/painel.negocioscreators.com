/* Service worker da Central NC: deixa instalar como app e recebe os avisos (web push) mandados pela VPS às 7h. */
self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (e) => e.waitUntil(self.clients.claim()));
self.addEventListener("fetch", (e) => {
  if (e.request.mode !== "navigate") return;
  e.respondWith(fetch(e.request).catch(() => new Response(
    '<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><body style="font-family:system-ui;background:#F3EBDF;color:#5A3A2E;padding:32px"><h2>Sem internet</h2><p>A Central precisa de conexão. Tente de novo quando voltar.</p></body>',
    { headers: { "Content-Type": "text/html; charset=utf-8" } })));
});
self.addEventListener("push", (e) => {
  let d = {};
  try { d = e.data ? e.data.json() : {}; } catch (x) { d = { body: e.data ? e.data.text() : "" }; }
  e.waitUntil(self.registration.showNotification(d.title || "Central NC", {
    body: d.body || "", tag: d.tag || "agenda", renotify: true,
    icon: "icon-192.png", badge: "icon-192.png", data: { url: d.url || "/central/#agenda" }
  }));
});
self.addEventListener("notificationclick", (e) => {
  e.notification.close();
  const url = (e.notification.data && e.notification.data.url) || "/central/#agenda";
  e.waitUntil(self.clients.matchAll({ type: "window", includeUncontrolled: true }).then((cs) => {
    for (const c of cs) if (c.url.includes("/central/") && "focus" in c) { c.navigate(url); return c.focus(); }
    return self.clients.openWindow(url);
  }));
});
