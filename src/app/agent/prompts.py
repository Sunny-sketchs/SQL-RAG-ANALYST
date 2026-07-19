ROUTER_PROMPT = """Classify the question as sql, rag, or hybrid.

sql: needs only structured sales data (orders, revenue, quantities, dates,
teams, products, channels). Multi-part questions where every part is a data
question are still sql.

rag: needs only company policy documents (commission, discounts, quota,
expense/travel). Multi-part questions where every part is policy are still
rag.

hybrid: at least one part needs sales data AND at least one part needs
policy. Number of clauses doesn't decide the route — what each clause needs
does. A single clause can need both (e.g. "does this comply with policy?").

Examples:
"How many orders in Q2 and what was the average discount?" -> sql
"What is the commission threshold and the quota exception policy?" -> rag
"What is the parking policy, and what is our total order quantity?" -> hybrid
"Does a 25% discount comply with commission policy?" -> hybrid

Question: {query}
Answer with exactly one word: sql, rag, or hybrid.
"""

SQL_GEN_PROMPT = """PostgreSQL expert. Write one read-only SELECT to answer the question.
No INSERT/UPDATE/DELETE/DROP/multiple statements. Add LIMIT if not implied by an aggregate.

Schema:
sales(id, order_number, sales_channel, warehouse_code, procured_date, order_date,
      ship_date, delivery_date, currency_code, sales_team_id, customer_id, store_id,
      product_id, order_quantity, discount_applied, unit_cost, unit_price)

Rules:
- Concepts not in this schema (e.g. "top performers", "remote employees",
  "commission tier") belong to policy docs, not this table. Never invent a
  filter/alias/value for them. If the question mixes a real data part with a
  non-schema concept, answer only the data part as if the rest weren't asked
  (e.g. "commission tier for top performers and average unit price" ->
  SELECT AVG(unit_price) FROM sales — nothing about tiers/performers).
- discount_applied is a fraction: 20% = 0.20, not 20.
- Text columns (sales_channel, warehouse_code, order_number, etc.) compared
  to a literal: use ILIKE, not = (casing is unknown).
- sales_team_id, customer_id, store_id, product_id are plain integers.
  "Team 28" -> WHERE sales_team_id = 28, not a quoted string.
- Four date columns: procured_date=stock purchased, order_date=customer
  ordered, ship_date=left warehouse, delivery_date=arrived. Default to
  order_date for ambiguous time references unless shipped/delivered/procured
  is stated.
- Never build partial date strings like '10-01'. For quarters use
  EXTRACT(QUARTER FROM column) = N, not date ranges, unless a year is given.
- "Revenue" = net of discount by default:
  SUM(order_quantity * unit_price * (1 - discount_applied)).
- "Revenue" = net of discount by default:
  SUM(order_quantity * unit_price * (1 - discount_applied)).
- "Profit" = (unit_price - unit_cost) * order_quantity, before discount,
  unless the question explicitly asks for discount-adjusted profit.

Question: {query}

Return ONLY the SQL query, no explanation, no markdown fences.
"""

SYNTHESIS_PROMPT = """Answer using ONLY the context below — no outside knowledge or
assumptions. If the answer isn't clearly supported by the context, say so rather than
guessing. Cite the source (SQL result or document name) for each claim.

A numeric result of 0 is a valid, complete answer — state it, don't treat it as missing.

For schedules across labeled periods (e.g. "Month 1-2", "Month 3-4"), count the actual
periods listed rather than estimating a total — show your reasoning if summarizing.
An open-ended range like "Month 5+" marks the point when a ramp is complete and the
standard rate applies — it is not part of the ramp and contributes zero months to any
ramp-length count.

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