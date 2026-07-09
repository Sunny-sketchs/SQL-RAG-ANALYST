ROUTER_PROMPT = """You are a routing agent for a sales analytics assistant.
Given a user question, decide whether it should be answered using:
- "sql": the question only needs structured sales data (orders, revenue,
  quantities, dates, teams, products, channels) — this includes multi-part
  questions where EVERY part is a data question (e.g. "how many orders in Q2
  and what was the average discount?" is still sql-only).
- "rag": the question only needs company policy documents (commission rules,
  discount approval, quota exceptions, expense/travel) — this includes
  multi-part questions where EVERY part is a policy question.
- "hybrid": the question has AT LEAST ONE part that needs sales data AND AT
  LEAST ONE part that needs policy documents. Only use hybrid when both types
  of information are genuinely required to fully answer the question.

The number of clauses or the presence of "and" does NOT determine the route —
what matters is whether the question needs data, policy, or both. A single
clause question can still need both (e.g. "does this order comply with
policy?" needs both the order's data and the policy text). A two-clause
question can still be single-route if both clauses need the same type of
information.

Examples:
- "How many orders in Q2 and what was the average discount?" -> sql (both
  clauses are data-only)
- "What is the commission threshold and what is the quota exception policy?"
  -> rag (both clauses are policy-only)
- "What is the parking reimbursement policy, and what is our total order
  quantity?" -> hybrid (one policy clause, one data clause)
- "Does a 25% discount comply with commission policy?" -> hybrid (requires
  policy text to know the rule, single clause)

Respond with exactly one word: sql, rag, or hybrid.

Question: {query}
"""

SQL_GEN_PROMPT = """You are a PostgreSQL expert. Given the table schema below, write a single
read-only SELECT query to answer the question. Never use INSERT, UPDATE, DELETE, DROP, or
multiple statements. Always include a LIMIT if not already implied by an aggregate.

Schema:
sales(id, order_number, sales_channel, warehouse_code, procured_date, order_date,
      ship_date, delivery_date, currency_code, sales_team_id, customer_id, store_id,
      product_id, order_quantity, discount_applied, unit_cost, unit_price)

CRITICAL: the question may contain concepts that do NOT exist in this schema
(e.g. "top performers", "remote employees", "commission tier", "standard
commission eligibility" — these belong to company policy documents, not this
table). Never invent a WHERE filter, column alias, or literal value to
represent a concept that has no corresponding column in the schema above.
If the question asks about such a concept alongside a real data question,
answer ONLY the data-only part exactly as if the non-schema concept were not
mentioned at all — do not filter, do not guess, do not fabricate a value.
For example: "What is the commission tier for top performers and what is the
average unit price?" should produce SELECT AVG(unit_price) FROM sales — nothing
about "top performers" or "commission tier", since neither exists in the schema.

IMPORTANT: discount_applied is stored as a decimal fraction, not a whole-number
percentage. A 20% discount is stored as 0.20, a 5% discount as 0.05. When the
question mentions a percentage (e.g. "discount above 20%"), convert it to the
decimal form in your WHERE clause (e.g. discount_applied > 0.20), not the raw
number (discount_applied > 20).

IMPORTANT: for any WHERE clause comparing a text column (sales_channel,
warehouse_code, order_number, etc.) against a literal string value, always use
case-insensitive comparison with ILIKE instead of =, since exact stored casing
is unknown (e.g. WHERE sales_channel ILIKE 'online', not
WHERE sales_channel = 'online').

IMPORTANT: sales_team_id, customer_id, store_id, and product_id are stored as
plain integers (e.g. 28, not "Team 28" or "TEAM-028"). When a question
references these using natural-language framing like "Team 28",
"Customer 15", or "Store 259", extract only the numeric value and compare
directly against the column as an integer (e.g. WHERE sales_team_id = 28),
never as a quoted string.

IMPORTANT: there are four date columns with distinct meanings —
procured_date (stock purchased), order_date (customer placed the order),
ship_date (left the warehouse), delivery_date (arrived at destination). For
any general or ambiguous time reference ("in June 2018", "last quarter",
"this year"), default to order_date unless the question explicitly says
"shipped", "delivered", or "procured".

IMPORTANT: never construct partial date strings like '10-01' — Postgres
cannot parse these as timestamps. For quarter-based filtering across all
years, use EXTRACT(QUARTER FROM column_name) = N (e.g.
WHERE EXTRACT(QUARTER FROM ship_date) = 4), not date range comparisons,
unless a specific year is explicitly stated in the question.

IMPORTANT: "total revenue" or "revenue" means net of discount by default —
SUM(order_quantity * unit_price * (1 - discount_applied)) — unless the
question explicitly asks for gross/pre-discount figures.

Question: {query}

Return ONLY the SQL query, no explanation, no markdown fences.
"""

SYNTHESIS_PROMPT = """Answer the user's question using ONLY the context provided below. Do not use
any outside knowledge, assumptions, or general familiarity with typical business policies — if the
answer isn't clearly supported by the SQL context or document context given here, say so explicitly
rather than filling the gap with plausible-sounding information.

Cite which source (SQL result or document name) supports each claim.

IMPORTANT: a numeric result of 0 is a valid, complete answer (e.g. "0 orders
match this condition") — do not treat a zero count or empty aggregate as
missing or insufficient context.

IMPORTANT: when a policy describes a schedule or range across labeled periods
(e.g. "Month 1-2", "Month 3-4"), do not perform arithmetic to summarize a
total unless you show your reasoning — count the actual periods listed
rather than guessing a round number. If asked for a total count derived from
listed items, count them explicitly rather than estimating.

Question: {query}

SQL context:
{sql_context}

Document context:
{rag_context}

Answer:
"""

GRADER_PROMPT = """Question: {question}
Expected fact (one valid correct answer, but other equally correct phrasings
of the same underlying truth should also be accepted): {expected_facts}
Actual answer: {answer}

Does the actual answer correctly and accurately address the question, even if
phrased differently from the expected fact? Reply with exactly one word: yes
or no."""