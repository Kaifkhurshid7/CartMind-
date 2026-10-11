"""Open CartMind's browser so YOU can sign in to Amazon / Flipkart once.

    python login.py

Sign in normally (OTP, 2FA, everything is yours to do), then close the window. The session is stored in
`browser_profile/` and reused by the agent. CartMind never sees or types your credentials.
"""

from playwright.sync_api import sync_playwright

from app.config import get_settings

SITES = ["https://www.amazon.in/gp/sign-in.html", "https://www.flipkart.com/account/login"]


def main() -> None:
    s = get_settings()
    with sync_playwright() as p:
        common = dict(user_data_dir=s.browser_profile_dir, headless=False, viewport={"width": 1366, "height": 820},
                      locale="en-IN")
        try:
            ctx = p.chromium.launch_persistent_context(channel=s.agent_browser_channel or None, **common)
        except Exception:  # noqa: BLE001  (Chrome not installed: use bundled Chromium)
            ctx = p.chromium.launch_persistent_context(**common)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(SITES[0])
        for url in SITES[1:]:
            ctx.new_page().goto(url)
        print("Sign in to each site in the window, then close the window to finish.")
        ctx.wait_for_event("close", timeout=0)
    print(f"Saved. Profile: {s.browser_profile_dir}")


if __name__ == "__main__":
    main()
