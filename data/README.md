# data/ — what Desk Buddy works with

Everything here is **fictional**: the store, the customers, the orders. Names and emails (`@example.com`) are made up,
and the card number in `q20` is the standard `4111 1111 1111 1111` test number.

| File | What it holds |
|---|---|
| `queries.json` | 24 customer messages, each with the correct answers ("gold labels") |
| `orders.json` | Customers, products and orders of **Pebble Store**, including charges, refunds and tracking |
| `policy.md` | The support policy Desk Buddy must follow (returns, refunds, delivery, when to hand over to a human) |

**"Today" is fixed at 2026-10-08** (`orders.json → as_of`), so date checks like "is this still returnable?" give the same
answer whenever you run the course.

## The queries

Every lesson step lets you pick from the queries tagged for it (`steps`). Steps 10–12 use all 24.

| Kind | Count | Why it's there |
|---|---|---|
| `clear` | 8 | Easy cases. Both sides should get them — compare speed, cost and output shape |
| `ambiguous` | 4 | More than one reasonable answer. Tests whether a model *knows* it is unsure |
| `typos` | 3 | Typos, shorthand, Hinglish |
| `angry` | 3 | Strong emotion or urgency — but still safe |
| `unsafe` | 3 | Prompt injection, a full card number, a threat against staff |
| `needs_code` | 3 | The right answer depends on dates or charges in the order record |

A query looks like this:

```json
{
  "id": "q02", "kind": "clear",
  "text": "My order debited amount 2 time. I want immediate help.",
  "customer_id": "C-1042", "order_id": "ORD-7731",
  "gold": {"team": "billing", "urgent": true, "frustration": 1, "intent": "duplicate_charge",
           "needs_human": false, "unsafe": false},
  "facts": {"duplicate_charge": true},
  "steps": [1, 2, 3, 4, 5, 6, 7, 8, 9],
  "teaches": "Clear billing case. ..."
}
```

- `also_ok` — for genuinely ambiguous queries, other answers that also count as correct.
- `facts` — ground truth that **code** works out from `orders.json` (step 06). The text alone can't tell you.
- `draft` — for the step 09 messages: a pre-written reply and whether it `answers_question` and is `on_policy`.
  Two drafts are good, three are flawed (a promise the policy doesn't allow, an invented product spec, a non-answer
  to an overdue refund). The first versions of two "good" drafts contained small unsupported promises ("free
  pickup", "usually quicker"); both judges caught them, so they were rewritten.

## How the gold labels were chosen

| Label | Values | Rule |
|---|---|---|
| `team` | `billing` | payments, charges, refunds, returns |
| | `shipping` | delivery, tracking, address changes, items damaged in transit |
| | `technical` | app or website errors |
| | `account` | login, password, profile |
| | `other` | product questions, thanks, anything else |
| `urgent` | `true` | the customer needs help **today**: money taken wrongly, a deadline today or tomorrow, can't do something time-critical. Saying "urgent" doesn't make it urgent; a calm message can be |
| `frustration` | `0` calm · `1` annoyed · `2` angry | `2` = shouting, insults, threats or repeated contact |
| `intent` | `order_status`, `duplicate_charge`, `refund_request`, `change_address`, `product_question`, `complaint`, `account_access`, `tech_issue`, `other` | what the customer wants done. A late-delivery credit or a return is a `refund_request` |
| `needs_human` | `true` | anything in policy §5: worth more than ₹10,000, chargeback or legal threat, threats, asks for a person, 3+ contacts in 30 days, overdue refund |
| `unsafe` | `true` | prompt injection, full card number / CVV / password / OTP, threats against staff. Rude is not unsafe (see `q17`). A message can be unsafe **and** need a human (`q19`, `q21`) |

**Checked against two models.** Before the course was built, every query was labelled by JEV (`jev-1.13`) and by Gemini
(`gemini-3.5-flash`). Where **both** disagreed with a gold label, the label was reviewed against the rules above. Some
were fixed (e.g. `q23` is urgent: the customer believes money was taken wrongly). Others were kept because the right
answer needs the policy plus the order record, which the message alone doesn't show (e.g. `q17`: the refund is
overdue). Where only one model disagreed, the label stayed — those are the interesting cases in the lessons.

## Adding a query

1. Add it to `queries.json` with the next id, a `kind`, gold labels, and the `steps` that should offer it.
2. If it needs an order, add the order to `orders.json` (the `total` must equal the items).
3. Run `pytest tests/test_data.py`. It checks labels, references and `facts` against the order records.
