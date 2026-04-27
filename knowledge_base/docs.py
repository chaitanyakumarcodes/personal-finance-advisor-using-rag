"""
Financial Knowledge Base — Embedded documents for RAG retrieval.
"""

FINANCIAL_DOCUMENTS = [
    {
        "id": "50_30_20_rule",
        "title": "The 50/30/20 Budgeting Rule",
        "content": """The 50/30/20 rule is a simple, powerful budgeting framework.
        Allocate 50% of your after-tax income to needs (rent, groceries, utilities, EMIs).
        Allocate 30% to wants (dining out, entertainment, shopping, subscriptions).
        Allocate 20% to savings and investments (SIP, PPF, emergency fund, FD).
        For Indian households earning ₹50,000/month: ₹25,000 needs, ₹15,000 wants, ₹10,000 savings.
        If rent alone exceeds 30% of income, consider the 60/20/20 variant.
        Track spending weekly to stay within allocations. Automate savings on salary day."""
    },
    {
        "id": "food_spending",
        "title": "Optimizing Food & Dining Expenditure",
        "content": """Food spending is one of the top controllable expenses in urban India.
        Zomato and Swiggy delivery orders cost 40-60% more than cooking at home due to platform fees, packaging, and delivery charges.
        A single Swiggy order averaging ₹350 done daily = ₹10,500/month vs home cooking at ~₹3,000/month.
        Recommended limit: food delivery should be max 8-10% of monthly income.
        Strategy: batch cook on weekends, use office canteen for lunches, limit delivery to 2-3 times per week.
        Grocery apps like Blinkit/Zepto for staples are cheaper than delivery food.
        Meal planning saves 25-30% on overall food costs."""
    },
    {
        "id": "sip_investing",
        "title": "SIP (Systematic Investment Plan) Basics",
        "content": """A Systematic Investment Plan (SIP) lets you invest a fixed amount in mutual funds every month.
        Even ₹500/month in a diversified equity fund can grow significantly over 10 years via rupee cost averaging.
        Historical average equity mutual fund return in India: 12-15% CAGR over 10+ year periods.
        ₹5,000/month SIP for 20 years at 12% CAGR = approximately ₹49.9 lakhs corpus.
        Start SIPs on salary day before spending — pay yourself first principle.
        Recommended funds for beginners: large-cap index funds tracking Nifty 50, flexi-cap funds.
        Increase SIP by 10% every year with salary hikes (step-up SIP).
        Do not stop SIPs during market downturns — you buy more units at lower prices."""
    },
    {
        "id": "emergency_fund",
        "title": "Emergency Fund — The Financial Safety Net",
        "content": """An emergency fund is 3-6 months of living expenses kept in liquid, safe instruments.
        For a person spending ₹40,000/month, emergency fund target = ₹1.2 to ₹2.4 lakhs.
        Keep emergency funds in: liquid mutual funds, high-yield savings accounts, or short-term FDs.
        Never invest emergency funds in equity or volatile assets.
        Build emergency fund before starting aggressive investments.
        Replenish immediately after any withdrawal.
        Liquid funds offer better returns than savings accounts (5-6%) with same-day redemption."""
    },
    {
        "id": "transport_costs",
        "title": "Optimizing Transportation Expenses",
        "content": """Transportation is a major expense in Indian metros.
        Cab apps (Ola/Uber) can cost 3-5x more than autos or metro for the same route.
        Monthly metro pass in major cities: ₹900-2,000 — saves significantly vs daily cab rides.
        Two-wheeler ownership: EMI + fuel + maintenance = ₹4,000-6,000/month, often cheaper than cabs.
        Carpooling apps can reduce cab costs by 50-60%.
        Track per-km cost: Uber averages ₹12-20/km vs metro at ₹2-4/km.
        Recommended: keep transport under 10-15% of monthly income.
        Work-from-home days directly reduce transport costs — optimize office visits."""
    },
    {
        "id": "subscription_audit",
        "title": "Subscription Audit — Eliminating Waste",
        "content": """The average urban Indian has 8-12 active subscriptions spending ₹2,000-5,000/month unknowingly.
        Common subscriptions: Netflix, Hotstar, Spotify, Amazon Prime, YouTube Premium, LinkedIn, gym, news apps.
        Audit all subscriptions quarterly — cancel anything unused for 30+ days.
        Share family plans: Netflix/Hotstar allow 4-5 screens — split costs with family.
        Annual plans are typically 15-30% cheaper than monthly.
        Free alternatives: YouTube (vs Spotify), JioCinema (vs Netflix for IPL), public libraries.
        Consolidate streaming: rotate subscriptions rather than maintaining all simultaneously.
        Saving ₹2,000/month on subscriptions = ₹24,000/year = significant SIP contribution."""
    },
    {
        "id": "debt_management",
        "title": "Managing Loans and Credit Card Debt",
        "content": """Credit card debt at 36-42% annual interest is the most dangerous financial trap.
        Always pay full credit card statement balance, never minimum due.
        Minimum due payment strategy: bank's profit, your loss — interest compounds daily.
        Debt avalanche: pay highest-interest debt first while making minimums on others.
        Debt snowball: pay smallest balance first for psychological wins — then tackle larger debts.
        Personal loan interest: 12-18% — use only for genuine emergencies, never lifestyle.
        EMI should not exceed 40% of take-home pay (all EMIs combined).
        Consider balance transfer to lower-interest card if carrying credit card debt.
        Prepay home loan when possible — saves lakhs in long-term interest."""
    },
    {
        "id": "savings_rate",
        "title": "Savings Rate and Wealth Building",
        "content": """Savings rate (savings / income) is the single most important metric for wealth building.
        A 10% savings rate means you need 9x your annual spending to retire.
        A 50% savings rate means you need only 17 years of working to retire comfortably.
        Increasing savings from 10% to 20% can cut your working years by a decade.
        In India, prioritize: EPF/PPF (tax-free) → ELSS (tax saving) → NPS → Equity MF → Debt MF.
        EPF gives guaranteed 8.15% tax-free — maximize this first.
        Tax saving under 80C: ₹1.5 lakh limit — use ELSS for highest return potential.
        Goal-based saving: name each SIP (vacation fund, home down payment) for emotional commitment."""
    },
    {
        "id": "shopping_control",
        "title": "Controlling Impulse Shopping and Lifestyle Inflation",
        "content": """Lifestyle inflation — spending more as you earn more — is the silent wealth killer.
        E-commerce apps use dark patterns: limited-time deals, flash sales, 'only 2 left' urgency.
        The 48-hour rule: add items to cart, wait 48 hours before purchasing — eliminates 60% of impulse buys.
        Wishlist method: move desired items to wishlist, review monthly — want often fades.
        Unsubscribe from promotional emails and disable sale notifications from apps.
        Amazon, Flipkart sales rarely offer the best prices — compare on PriceSpy or Camelcamelcamel.
        Buy quality over quantity: one ₹3,000 item lasting 3 years vs three ₹1,000 items = same cost, less clutter."""
    },
    {
        "id": "utility_optimization",
        "title": "Utilities and Bills Optimization",
        "content": """Utility bills (electricity, internet, phone) are often set-and-forget — but savings are real.
        Electricity: AC at 24C vs 18C uses 30% less power. LED bulbs save ₹500-1,000/year over incandescent.
        Internet: competitive bids from Airtel/Jio/BSNL often yield 20-30% better plans.
        Mobile: evaluate if postpaid plan matches actual usage vs prepaid alternatives.
        Water heater: timer switches save 20-30% on geyser electricity costs.
        Review insurance premiums annually — compare online aggregators for better rates.
        Group insurance through employer is typically 40-60% cheaper than individual policies."""
    },
    {
        "id": "investment_basics",
        "title": "Investment Basics for Beginners — Indian Context",
        "content": """Investment hierarchy for Indian salaried professionals:
        1. Emergency fund (3-6 months expenses) in liquid fund
        2. Health insurance (₹5-10 lakh cover) — most important protection
        3. Term life insurance if dependents exist
        4. EPF maximization (employer match is free money)
        5. PPF (₹1.5 lakh/year — EEE tax status, guaranteed 7.1%)
        6. ELSS mutual funds for 80C benefits with equity upside
        7. NPS for additional ₹50,000 deduction under 80CCD(1B)
        8. Remaining in diversified equity mutual funds via SIP
        Never: MLM schemes, unsolicited stock tips, cryptocurrency speculation with essential funds.
        Rule of thumb: equity allocation % = 100 minus your age."""
    },
    {
        "id": "anomaly_response",
        "title": "Responding to Unusual or Spike Transactions",
        "content": """Sudden transaction spikes often indicate: impulse purchases, subscription renewals, or fraud.
        If an unusual transaction appears: verify with bank statement, check for subscription auto-renewals.
        Medical emergency spikes: ensure health insurance claims are filed promptly.
        Travel spikes: evaluate if credit card travel benefits could offset future costs.
        Irregular income months (bonuses, freelance): allocate windfalls — 50% invest, 30% debt, 20% treat.
        Annual expense spikes (insurance, property tax, maintenance): pre-fund via monthly sinking fund.
        Divide annual irregular expenses by 12 and save monthly — prevents cash flow shocks."""
    },
    {
        "id": "financial_goals",
        "title": "Setting and Achieving Financial Goals",
        "content": """Financial goals need to be SMART: Specific, Measurable, Achievable, Relevant, Time-bound.
        Short-term (< 1 year): vacation, gadget purchase → liquid/debt funds.
        Medium-term (1-5 years): car, home down payment → hybrid/balanced funds.
        Long-term (5+ years): retirement, children's education → equity funds.
        Reverse calculation: goal ₹10 lakh in 5 years at 12% return → need ₹12,244/month SIP.
        Track net worth monthly: assets (investments + savings) minus liabilities (loans + dues).
        Net worth growing = financial health. Flat or declining = immediate review needed."""
    }
]


def get_all_documents():
    return FINANCIAL_DOCUMENTS

def get_document_texts():
    return [doc["content"] for doc in FINANCIAL_DOCUMENTS]

def get_document_ids():
    return [doc["id"] for doc in FINANCIAL_DOCUMENTS]