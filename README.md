# CartMind — Autonomous AI Shopping Agent

> Tell CartMind what you want. It finds the best option and shops for you.

CartMind turns a natural-language shopping request into a workflow: it extracts requirements, researches and
filters products, compares and scores them, explains its recommendation, **asks for your approval**, and then
drives a real browser (Playwright) to find the product, verify its price and add it to the cart. It always stops
before payment.

**Gemini thinks. LangGraph controls. LangChain connects. Playwright acts. CartMind delivers.**

## How it works

```
React UI ──HTTP/SSE──▶ FastAPI ──▶ LangGraph workflow ──▶ LangChain tools ──▶ Search / Reviews / Playwright
```

```
requirements → validate → research → filter ─┬→ compare → reviews → select → recommend
                                              └→ replan (near-misses, no exact match)
recommend → approval (human-in-the-loop interrupt) ─┬→ cancel
                                                    └→ shop (Playwright) ─┬→ added to cart ✔
                                                                          ├→ price changed → ask user → shop
                                                                          ├→ unavailable / not found → next best → approval
                                                                          └→ failure → explained, nothing pretended
```

| Concern | Where |
|---|---|
| Graph, nodes, state | `backend/app/agents/` |
| LangChain tools (search, product, reviews, Playwright) | `backend/app/tools/` |
| Gemini client, key rotation, Groq fallback, prompts | `backend/app/llm/` |
| Optional RAG knowledge base | `backend/app/rag/`, `knowledge_base/documents/` |
| REST + SSE API | `backend/app/api/` |
| Live Amazon.in adapter (search + add to cart) | `backend/app/tools/amazon_tool.py` |
| Offline demo store | `backend/app/store/` |
| React UI | `frontend/src/` |

### Design decisions

- **A real browsing agent (default).** With `SHOPPING_MODE=agent` an LLM (Gemini, free key) drives a **visible
  Chrome window**: each step it sees the live page (URL, numbered clickable elements, text) and picks one action:
  go to a URL, click, type, scroll, read more, ask you to do something. It starts at a search engine, opens
  Amazon.in / Flipkart, searches and filters there, records candidates, and after your approval opens the exact
  product page, confirms the price, and clicks *Add to Cart*.
- **You log in, CartMind never does.** The browser uses a persistent profile (`backend/browser_profile/`, git-ignored),
  so once you sign in to Amazon / Flipkart in that window it stays signed in. When a login, OTP or robot check
  appears, the agent pauses and the UI shows *"I'm done, continue"*. It never types credentials or solves CAPTCHAs.
- **Guardrails are code, not prompts.** Buy Now / Proceed to Buy / Checkout / payment clicks and URLs are refused;
  Add to Cart is refused until the displayed price was confirmed; only allow-listed domains open; passwords,
  card and OTP fields can't be typed into. The agent's "I added it" is never trusted: the cart page is re-opened
  and the item must actually be there.
- **Modes.** `agent` (above) needs an LLM key and falls back to `live` (a fixed Amazon.in script) if none is set.
  `demo` is the offline built-in store used by the tests.
- **Trust floor for live listings.** A scraped listing is only recommended if it has 10+ reviews and 3.5★+, and
  a mandatory spec (RAM, storage, ANC...) must actually be stated in its title. Unknown beats wrong.
- **Never past the cart.** CartMind does not click *Buy Now*, enter payment details, or log in. "Buy" means
  "added to your cart, ready for you to check out".
- **No bot-evasion.** If Amazon shows a robot check, CartMind stops and says so. With
  `PLAYWRIGHT_HEADLESS=false` it waits for *you* to solve it in the visible browser window.
- **Works without an API key.** Every Gemini call has a rule-based fallback (extraction, scoring, templated
  explanations), so the whole flow runs offline. With keys, Gemini writes the extraction, comparison,
  review summaries, explanations and Q&A.
- **Scoring is deterministic**, the LLM explains it. Suitability scores come from Python (spec fit, Bayesian
  rating, value, priorities), so recommendations are reproducible and never hallucinated.
- **Approval is a hard gate.** The graph pauses on a LangGraph `interrupt`; only an explicit
  `approved: true` resumes it. Typing "add it to cart" in chat only opens the approval dialog.
- **No payment, no card data.** The flow ends at the cart.

## Quick start

Requirements: Python 3.10+, Node 18+.

```bash
cp .env.example .env            # add GEMINI_API_KEY_1 (optional but recommended)

# backend
cd backend
python -m venv .venv && source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
uvicorn app.main:app --port 8000

# frontend (new terminal)
cd frontend
npm install
npm run dev                      # http://localhost:5173
```

Or with Docker: `docker compose up --build` → UI on <http://localhost:3000>, API on <http://localhost:8000/docs>.

Set `PLAYWRIGHT_HEADLESS=false` to watch the browser work.

> Live mode drives a real shopping site at human pace for personal use, and you approve every action. Amazon's
> terms restrict automated access, so use it responsibly and don't run it at volume.

## API

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/shopping/start` | Start a session `{query}` |
| GET | `/api/shopping/{id}` | Full session state |
| GET | `/api/shopping/{id}/status` | Status + current step |
| GET | `/api/shopping/{id}/recommendations` | Recommendation, alternatives, comparison |
| GET | `/api/shopping/{id}/events` | SSE stream of agent activity |
| POST | `/api/shopping/{id}/approve` | `{approved, product_id?, accept_price_change?}` |
| POST | `/api/shopping/{id}/execute` | Approve the current recommendation |
| POST | `/api/shopping/{id}/cancel` | Cancel |
| POST | `/api/chat/{id}` | Q&A, refinement (replanning), approval/cancel intents |
| GET | `/api/shopping/sessions` | History |
| GET | `/store/...` | The demo shopping site |

Session statuses: `running`, `waiting_for_approval`, `executing`, `price_changed`, `completed`, `cancelled`,
`failed`, `no_results`, `needs_clarification`.

## Configuration

See `.env.example`. Gemini keys `GEMINI_API_KEY_1..3` are rotated automatically when one hits a quota limit;
`GROQ_API_KEY` enables an optional fallback provider. Keys live only on the backend.

## Tests

```bash
backend/.venv/bin/python -m pytest        # Windows: backend\.venv\Scripts\python -m pytest
```

Covers requirement extraction, filtering, scoring, tools, key rotation, the full LangGraph flow (approval,
decline, alternative pick, unavailable product, price change, no results, replanning), the HTTP API and SSE,
and real-Chromium Playwright runs including website-unreachable and timeout failures. Tests run without any
API key.

## First run with your accounts

```bash
cd backend
python login.py        # opens Chrome: sign in to Amazon and Flipkart yourself, then close the window
```

Then start the app as above. Get a free Gemini key at <https://aistudio.google.com/apikey> and put it in `.env`
as `GEMINI_API_KEY_1` (the browsing agent needs a model to decide what to click).
