SYSTEM = (
    "You are CartMind, an autonomous AI shopping assistant for Indian shoppers. Prices are in INR (₹). "
    "Be concise, concrete and honest. Only use facts present in the provided data; never invent specs, prices or reviews."
)

EXTRACT_REQUIREMENTS = """Convert the shopping request into structured requirements.

Request: "{query}"

Return ONLY JSON in exactly this shape:
{{
  "category": "laptop | headphones | phone | <other single noun>",
  "budget": {{"maximum": <number or null>, "currency": "INR"}},
  "use_case": "<short string or null>",
  "requirements": {{ "<spec>": "<value>" }},
  "preferences": ["<nice-to-have>"],
  "priorities": ["<what matters most, e.g. battery, performance, display, price>"],
  "location": "India"
}}

Rules:
- "requirements" are MANDATORY specs. Use keys like ram, storage, battery, anc, display, camera.
  Express minimums as "16GB+", "512GB+", "30 hours+"; booleans as "yes".
- Convert "50k" to 50000. Category must be singular lowercase ("headphones" stays "headphones").
- Things the user says they would "prefer" or "like" go in "preferences", not "requirements".
- Do not invent requirements the user did not state."""

MERGE_REQUIREMENTS = """The user is refining an ongoing shopping search.

Current requirements (JSON):
{current}

User's new message: "{message}"

Update the requirements to reflect the message (change the budget, add/remove mandatory specs, adjust
priorities and preferences). Keep everything the user did not change. Return ONLY the full updated JSON in the
same shape as the current requirements."""

COMPARE = """User requirements:
{requirements}

Shortlisted products (best score first), as JSON:
{products}

Write a short comparison for the shopper (max 120 words, plain text, no markdown tables). Say which product
leads on which criterion (price, performance, battery, display, reviews) and mention trade-offs."""

REVIEW_SUMMARY = """Summarise customer reviews for each product below in ONE sentence each.
Return ONLY JSON: {{"<product_id>": "<one-sentence summary>", ...}}

Products and review snippets:
{reviews}"""

RECOMMEND = """User requirements:
{requirements}

Recommended product:
{product}

Runner-up alternatives:
{alternatives}

Write the recommendation as JSON:
{{
  "summary": "<2-3 sentences: why this product best matches the requirements>",
  "reasons": ["<short reason>", "..."],
  "disadvantages": ["<honest drawback>", "..."],
  "alternative_note": "<one sentence comparing with the main alternative>"
}}
Return ONLY JSON. Use only facts from the data."""

CLASSIFY_INTENT = """A shopper is chatting with a shopping agent. Classify their latest message.

Current requirements: {requirements}
Latest message: "{message}"

Return ONLY JSON: {{"intent": "<one of: question | refine | approve | cancel>"}}
- question: asks about products, specs, reasoning, or general product knowledge
- refine: changes budget, specs, priorities or category and implies a new search ("increase budget to 60k", "I want ANC")
- approve: asks the agent to add the recommended product to the cart / buy it
- cancel: wants to stop the whole task"""

ANSWER = """You are answering a shopper's question about their ongoing search.

Requirements: {requirements}
Shortlisted products: {products}
Current recommendation: {recommendation}
Comparison: {comparison}
Background knowledge (may be empty):
{context}

Conversation so far:
{history}

Question: "{question}"

Answer helpfully in at most 120 words, grounded in the data above. If the question compares products, use their
actual specs and prices. If it is general product knowledge, answer from your knowledge."""

EXPLAIN_ERROR = """A shopping automation step failed. Explain it to the shopper in 1-2 friendly sentences and
suggest the next step.

Error: {error}
Product: {product}"""

IMPROVE_PROMPT = """Rewrite this shopping request so a shopping agent can act on it precisely.

Request: "{text}"

Rules:
- Keep the user's intent, product and every number they gave. Do not invent a budget, brand or spec.
- State mandatory requirements (budget, key specs) clearly, then preferences.
- One or two sentences, plain text. Return ONLY the rewritten request, nothing else."""
