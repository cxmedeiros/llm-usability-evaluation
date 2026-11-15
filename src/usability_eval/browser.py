"""Adaptador síncrono para uma sessão Chromium isolada por execução."""

from datetime import datetime, timezone
from pathlib import Path
from types import TracebackType

from playwright.sync_api import ElementHandle, sync_playwright

from usability_eval.schemas import Action, Element, Evidence, Observation


class BrowserSession:
    """IDs locais apontam para os nós observados, nunca para um novo nth locator."""

    def __init__(self, *, timeout_ms: int = 5000, headless: bool = True):
        self.timeout_ms = timeout_ms
        self.headless = headless
        self._targets: dict[str, ElementHandle] = {}

    def __enter__(self):
        self._playwright = sync_playwright().start()
        try:
            self._browser = self._playwright.chromium.launch(headless=self.headless)
            self._context = self._browser.new_context(
                viewport={"width": 1280, "height": 720}, locale="pt-BR",
                timezone_id="America/Recife", reduced_motion="reduce",
            )
            self._context.tracing.start(screenshots=True, snapshots=True)
            self.page = self._context.new_page()
            self.page.set_default_timeout(self.timeout_ms)
            self.page.set_default_navigation_timeout(self.timeout_ms)
            return self
        except Exception:
            self.__exit__(None, None, None)
            raise

    def __exit__(self, exc_type: type | None, exc: BaseException | None,
                 traceback: TracebackType | None):
        try:
            if hasattr(self, "_browser"):
                self._browser.close()
        finally:
            self._playwright.stop()

    def navigate(self, url: str):
        response = self.page.goto(url, wait_until="domcontentloaded")
        if response is not None and response.status >= 400:
            raise RuntimeError(f"HTTP {response.status}: {url}")

    def observe(self) -> Observation:
        for handle in self._targets.values():
            handle.dispose()
        self._targets.clear()
        elements = []
        handles = self.page.query_selector_all(
            "a[href],button,input:not([type=hidden]),textarea,select,[role],[tabindex]"
        )
        for handle in handles:
            if not handle.is_visible():
                handle.dispose()
                continue
            metadata = handle.evaluate("""el => {
                const tag = el.tagName.toLowerCase();
                const role = el.getAttribute('role') || ({a: 'link', button: 'button',
                    textarea: 'textbox', select: 'combobox', input:
                    ['submit', 'button', 'reset'].includes(el.type) ? 'button' :
                    ({checkbox: 'checkbox', radio: 'radio'}[el.type] || 'textbox')})[tag]
                    || 'generic';
                const labelledBy = (el.getAttribute('aria-labelledby') || '')
                    .split(/\\s+/).filter(Boolean)
                    .map(id => document.getElementById(id)?.innerText || '').join(' ').trim();
                const labels = Array.from(el.labels || []).map(l => l.innerText).join(' ').trim();
                const name = labelledBy || el.getAttribute('aria-label') || labels ||
                    el.innerText || (role === 'button' ? el.value : '') ||
                    el.getAttribute('placeholder') || el.getAttribute('title') || '';
                return {role, name: name.trim()};
            }""")
            target_id = f"e{len(elements)}"
            self._targets[target_id] = handle
            elements.append(Element(id=target_id, enabled=handle.is_enabled(), **metadata))
        return Observation(
            recorded_at=datetime.now(timezone.utc), url=self.page.url,
            title=self.page.title(), visible_text=self.page.locator("body").inner_text(),
            elements=elements,
        )

    def execute(self, action: Action):
        if action.kind == "navigate":
            self.navigate(str(action.url))
        elif action.kind == "scroll":
            self.page.evaluate("delta => window.scrollBy(0, delta)", action.delta_y)
        else:
            target = self._targets[action.target_id]
            if action.kind == "click":
                target.click()
            elif action.kind == "fill":
                target.fill(action.value)
            elif action.kind == "select":
                target.select_option(value=action.value)
            elif action.kind == "press":
                target.press(action.key)

    def capture(self, observation: Observation, directory: Path) -> Evidence:
        relative = f"screenshots/{observation.id}.png"
        path = directory / relative
        path.parent.mkdir(exist_ok=True)
        self.page.screenshot(path=str(path), animations="disabled")
        return Evidence(
            observation_id=observation.id, kind="screenshot", artifact_path=relative,
            description="Captura do viewport após a observação.",
        )

    def stop_trace(self, directory: Path, observation: Observation | None) -> Evidence | None:
        self._context.tracing.stop(path=str(directory / "trace.zip"))
        if observation is None:
            return None
        return Evidence(
            observation_id=observation.id, kind="trace", artifact_path="trace.zip",
            description="Trace da sessão completa; observação final como referência.",
        )
