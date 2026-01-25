PROJECT: ASPIR One-Page Promotion + Registration + Paystack Payment

GOAL
Build a single, high-converting landing page for the ASPIR Mentorship Program (Elevate Tribe Analytics) that:
1) Explains the program clearly (what it is, who it’s for, how it works)
2) Captures registration details (student + parent/guardian where applicable)
3) Takes payment via Paystack
4) After successful payment, shows a confirmation page + sends confirmation email (optional v1)
5) Stores registration and payment status in a database for admin tracking

BRAND & UI DIRECTION
- Clean, modern, calm and professional
- Use white space
- Primary brand color: Elevate Green (use the existing logo color feel)
- Simple section layout, easy to scan
- CTA buttons: "Register & Pay"
- Page should be mobile-first and fast

TECH STACK
Frontend: React (Next.js recommended)
Backend: Django (Django REST Framework)
Database: PostgreSQL (or SQLite for dev)
Payments: Paystack (standard checkout or inline)
Hosting: (later) Hetzner or VPS

LANDING PAGE SECTIONS (ONE PAGE)
1) Hero section
   - Title: "ASPIR Mentorship Program"
   - Subtitle: "A step-by-step journey to Purpose, Excellence & Leadership"
   - CTA: "Register & Pay"
   - Small trust line: "By Elevate Tribe Analytics"
   - Optional: short bullet outcomes (3-5)

2) What is ASPIR?
   - Brief paragraph
   - ASPIR meaning list (A, S, P, I, R)

3) How it works
   - Cohort-based
   - Two groups: 10–15 and 16–22
   - Learners register and pay PER DIMENSION (A, S, P, I, R)

4) Pricing (very clear)
   - New Learners: $50 registration + $100 course = $150 (first dimension)
   - Returning Learners: $20 registration + $100 course = $120 (next dimension)
   - Note: payment is per dimension selected

5) Registration form (embedded on same page)
   Required fields:
   - Full Name (student)
   - Email
   - Phone/WhatsApp
   - Country
   - Age
   - Select Group (auto-suggest based on age, but allow manual choice):
       Group 1: 10–15
       Group 2: 16–22
   - Select Cohort:
       Cohort 2 (new intake)
       Cohort 1 (returning)
   - Select ASPIR Dimension to register for:
       A: Academic Excellence (Redefined)
       S: Spiritual Growth
       P: Purpose Discovery
       I: Impactful Leadership
       R: Refined Communication
   - Select Enrollment Type:
       New Learner (first time) -> amount = 150
       Returning Learner (continuing) -> amount = 120
   Extra fields (recommended):
   - Parent/Guardian Name (required if age < 16)
   - Parent/Guardian Phone (required if age < 16)
   - How did you hear about us? (optional)

6) Payment section
   - On form submit:
     a) Validate inputs
     b) Create a "registration" record with status = "pending"
     c) Initialize Paystack transaction with:
        - email
        - amount (in kobo/lowest currency unit)
        - reference (unique)
        - metadata: cohort, group, dimension, enrollmentType, studentName, phone
     d) Redirect user to Paystack checkout OR open Paystack inline modal
   - After payment:
     e) Paystack calls webhook -> verify transaction server-side
     f) Update registration status = "paid"
     g) Show success page: "Payment successful. Welcome to ASPIR."
     h) Display summary: name, cohort, group, dimension, receipt reference

PAYMENTS & WEBHOOKS (BACKEND)
Endpoints:
- POST /api/registrations/initialize-payment
  Body: registration form data
  Response: authorization_url (or Paystack data) + reference

- GET /api/registrations/verify?reference=xxx
  Verifies with Paystack + returns registration status

- POST /api/paystack/webhook
  Validate signature header from Paystack
  On "charge.success":
    - verify with Paystack API
    - mark registration as paid
    - store transaction details

DATABASE MODELS (MINIMUM)
Registration:
- id (uuid)
- full_name
- email
- phone
- country
- age
- group (G1 or G2)
- cohort (C1 or C2)
- dimension (A/S/P/I/R)
- enrollment_type (NEW/RETURNING)
- amount
- currency
- status (PENDING/PAID/FAILED)
- paystack_reference
- created_at

Transaction:
- id
- registration_id (FK)
- reference
- amount
- currency
- paid_at
- channel
- raw_payload (JSON)
- created_at

ADMIN NEEDS (MINIMUM)
- Simple admin page or Django admin:
  - list registrations
  - filter by status/cohort/group/dimension
  - export CSV

SECURITY & QUALITY
- Server-side verification of Paystack transaction (never trust frontend)
- Webhook signature validation
- Rate limit initialize endpoint (basic)
- Basic spam protection (simple honeypot field)

USER EXPERIENCE DETAILS
- Form should auto-calculate amount based on enrollment type
- If age < 16:
  - show guardian fields and make required
- After successful payment:
  - show confirmation
  - email confirmation (optional in v1)

DELIVERABLE
A working landing page that accepts registration and payment, stores records, and confirms payment success.