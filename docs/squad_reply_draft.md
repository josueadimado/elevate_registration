# Draft reply to Squad support

You can send something like this to Squad's tech team:

---

Hi,

Thank you for the clarification. We’ve implemented it as follows:

- **NGN transactions** → we use Naira only for customers paying with Naira (Nigerian) cards.
- **USD transactions** → we use USD for customers paying with foreign/international cards.

Our challenge is that many of our payers are **not in Nigeria**. They are in Ghana, US, Canada, UK, etc., and their cards are in their local currency (e.g. GHS, USD, CAD, GBP). We don’t know the card currency until the customer is on the payment page.

Our understanding is:

- When we initiate a **USD** transaction (`currency_id`: `"USD"`), the charge is in USD. The customer’s bank (in Ghana, US, Canada, UK, etc.) will convert from the card’s local currency to USD if needed. So one USD link works for all these countries.
- When we initiate an **NGN** transaction, we use it only for Nigerian Naira cards.

Could you confirm that:

1. Initiating with **USD** is correct for cards issued in Ghana, US, Canada, UK (and that the cardholder’s bank handles conversion to USD)?
2. We should use **NGN** only when we know the customer is paying with a Naira card?

We’ve added two options on our payment page: “Pay in Naira (₦)” for Naira cards and “Pay in USD ($) — for international cards,” and we direct international customers to the USD option.

Thanks,  
[Your name]

---

**Note:** In their message they wrote `"currency_id":"USD"` for both cases; the Naira one was likely a typo and should be **NGN** for Naira transactions.
