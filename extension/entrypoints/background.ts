const SERVER_URL = 'http://localhost:8000';

export default defineBackground(() => {
  // Ponte HTTP: o content script roda na página HTTPS do fornecedor e não
  // pode chamar o server em http://localhost (mixed content bloqueado pelo
  // navegador). O background script, em contexto privilegiado, pode.
  browser.runtime.onMessage.addListener((message, _sender, sendResponse) => {
    if (message?.type !== 'iris:hub-request') return;

    const { path, method = 'GET', body } = message;

    fetch(`${SERVER_URL}${path}`, {
      method,
      headers: body ? { 'Content-Type': 'application/json' } : undefined,
      body: body ? JSON.stringify(body) : undefined,
    })
      .then(async (response) => {
        sendResponse({ ok: response.ok, status: response.status, data: await response.json() });
      })
      .catch((error) => {
        sendResponse({ ok: false, error: String(error) });
      });

    return true;
  });
});
