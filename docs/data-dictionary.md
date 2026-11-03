# Data dictionary

**Version 1 (L02).** Every table of the v1.0.0 export (`legacy_csv`, 27 CSV
files) and every column: its type, what it means, and whether it is personal
data.

Where the content comes from:

- **Columns, row counts and every count below:** profiled from the CSV files on
  2026-10-20, reading every value as text.
- **Types:** the source schema, in the company repo's `db/migrations/`
  (PostgreSQL 17). Bronze types depend on how the export is landed
  ([ADR 0002](adr/)), and are added here once it is.
- **Meanings:** the schema, the company repo's
  [dataset card](https://github.com/TangoAI-AlbertSchool-Data-Eng-Cloud/albert-marketplace/blob/main/docs/dataset-card.md),
  and the data itself.

## Personal data: what the marks mean

| Mark | Means | Examples |
|---|---|---|
| **Yes · never ingest** | Credentials and card secrets. Deselected at extraction and never reach the platform ([ADR-0001](adr/0001-target-architecture.md)) | `customer.pwd`, `payment_details.card_no`, `cvv` |
| **Yes · contact** | Identifies or reaches one person directly | name, email, phone, street address |
| **Yes · location** | Where a person lives, coarser than the street | town, region, postcode, country |
| **Yes · card** | Card data that is not a secret | expiry date |
| **Yes · identifier** | A stable ID for one person. Pseudonymous, which is still personal data (GDPR Art. 4(5)) | `c_id`, `buyer_id`, `seller_id` |
| **Unclassified** | Free text and user uploads. They can contain anything, and the schema cannot tell | `review.r_desc`, `title`, `review_img` |
| **No** | Not about a person | prices, product data, dates, keys |

A column marked **No** can still sit in a row that belongs to one person: an
order date is not personal by itself, but an order row carries a `buyer_id`.
Each table's description says when its rows belong to a person.

**The index column.** 25 of the 27 files start with a column that has an empty
header: the row number pandas wrote when the export was made (0, 1, 2…). It
is not in the source tables. pandas reads it back as `Unnamed: 0`, and a
BigQuery CSV load names it `int64_field_0`. Only `order_items` and `payment`,
added after the original extract, do not have it. The tables below list it as
*(index)*.

## Where the personal data is

| Table | Personal columns |
|---|---|
| `customer` | `c_id`, `fname`, `lname`, `phone`, `email`, **`pwd`** |
| `payment_details` | **`card_no`**, **`cvv`**, `expiry_date`, `billing_address` |
| `shipping_details` | `street_address`, `city`, `state`, `zip`, `country`, `phone` |
| `buyer`, `orders`, `wishlist_item`, `cart`, `returns` | `buyer_id` |
| `review` | `buyer_id`; `r_desc` and `title` unclassified |
| `review_images` | `review_img` unclassified |
| `seller`, `seller_products`, `seller_reviews` | `seller_id` (and `seller.seller_name`, empty) |
| `customer_shipping`, `customer_payment`, `subscription` | `c_id` |

**Never ingested:** `customer.pwd`, `payment_details.card_no` and
`payment_details.cvv`, in bold above.

The other 11 tables hold no personal column: `product`, `category`,
`product_images`, `product_reviews`, `order_items`, `payment`, `shipment`,
`carrier`, `discount`, `daily_deals`, `cart_items`. `order_items` and `payment`
still belong to a buyer, through `orders`.

## Traps in the export

What a loader or a staging model has to know. Each trap belongs to exactly one
place in silver (L05).

| # | Trap | Where | What goes wrong |
|---|---|---|---|
| 1 | **An index column** with an empty header | 25 files, all but `order_items` and `payment` | It loads as an extra column (`Unnamed: 0`, `int64_field_0`) |
| 2 | **Leading zeros in text codes** | `customer.phone` (82,203 start with `0`), `shipping_details.phone` (125,861), `shipping_details.zip` (19,622), `p_id` (6 products, 30 order lines) | Read as numbers, they lose the zero: a 10-digit phone becomes 9 digits, and a `p_id` no longer joins |
| 3 | **Codes that already lost their zeros** | `payment_details.cvv`: 961 with one digit, 8,440 with two | Never ingested, but a reminder of what trap 2 does |
| 4 | **Strings that pandas reads as missing** | `customer.fname` (4), `review.r_desc` (13), `review.title` (21) | `None`, `NA`, `N/A`, `NULL` and `n/a` become nulls with pandas' defaults. Other spellings (`Na`, `none`) stay text |
| 5 | **Empty and blank text** | `product.p_name` (6 empty), `review.r_desc` (14 empty, 110 a single space) | Not null, but not a value either |
| 6 | **Every order twice** | `orders`, and so `order_items`, `payment`, `shipment` | Revenue and units doubled; `DISTINCT` on the order's columns removes only a fifth of the twins (L01) |
| 7 | **Float noise in prices** | `product.price` (35,205 with more than two decimals); 5 products under half a cent | Catalogue totals differ from what was paid (`price_at_purchase`, rounded to cents) |
| 8 | **Columns that are always empty** | `seller.seller_name`, `orders.discount_id` | A column of nulls that looks like data |
| 9 | **Columns with one value** | `payment.method`, `payment.status`, `review.seller_product_flag`, `shipment.shipment_type`, `customer_payment.is_default` | Nothing to filter or group on, and `seller_product_flag` contradicts the links |
| 10 | **Empty tables** | `cart`, `cart_items`, `daily_deals`, `discount`, `returns` | A model built on them returns nothing, not an error |
| 11 | **Inconsistent names** | `wishlist_item.product_id` for `p_id`; `shipping_details.state` holds European regions | Joins and meanings guessed from names go wrong |
| 12 | **A timestamp with no time zone** | `payment.created_at` | The day of a payment near midnight depends on the time zone assumed |
| 13 | **No constraints in the files** | All 27 | Keys and foreign keys hold in the source, but nothing in the CSVs enforces them |

## Still to add

- **Bronze types** (Till, ADR 0002).
- **The clickstream events** (L03, Jane).
- **Which path each table takes into bronze,** and the columns each path adds
  (L03, Till): the export, the extractor or the clickstream consumer. There is
  no Airbyte path: without a service account it cannot reach our bucket.

---

## People and accounts

### `customer` · 130,766 rows

Everyone with an account: 100,000 buyers and 30,766 sellers, no one both. One
row per person. Key: `c_id`.

| Column | Type | Meaning | Personal data | Notes |
|---|---|---|---|---|
| *(index)* | integer | Export row number | No | Not in the source table |
| `c_id` | varchar(40) | Customer ID. Equal to `buyer.buyer_id` or `seller.seller_id` | Yes · identifier | 25 to 36 characters. Buyer IDs are the pseudonymous user IDs of Amazon Reviews'23 |
| `fname` | varchar(200) | First name | Yes · contact | Synthetic. 4 are the strings `None`, `NA`, `N/A` and `NULL` |
| `lname` | varchar(30) | Last name | Yes · contact | Synthetic, 124 distinct values |
| `phone` | varchar(15) | Mobile phone, national format | Yes · contact | **Text, not a number:** 82,203 start with `0`. 9 to 12 digits. Unique |
| `email` | varchar(250) | Email address | Yes · contact | Synthetic. Unique |
| `pwd` | varchar(60) | Account password | **Yes · never ingest** | Plain text, no hash format, 12 to 20 characters |

### `buyer` · 100,000 rows

The customers who buy. Referenced by orders, reviews, wishlists, carts and
returns. Key: `buyer_id`, which is a `customer.c_id`.

| Column | Type | Meaning | Personal data | Notes |
|---|---|---|---|---|
| *(index)* | integer | Export row number | No | Not in the source table |
| `buyer_id` | varchar(40) | Buyer ID | Yes · identifier | 28 to 36 characters |

### `seller` · 30,766 rows

The independent sellers who list products. Key: `seller_id`, which is a
`customer.c_id`.

| Column | Type | Meaning | Personal data | Notes |
|---|---|---|---|---|
| *(index)* | integer | Export row number | No | Not in the source table |
| `seller_id` | varchar(40) | Seller ID | Yes · identifier | 25 to 30 characters |
| `seller_type` | varchar(200) | Kind of seller | No | `marketplace` or `third_party_seller` |
| `seller_name` | varchar(1000) | Seller's name | Yes · contact | **Empty in all 30,766 rows:** the schema declares it, the export has no values |

### `subscription` · 50,091 rows

Yearly paid subscriptions. Each row belongs to one buyer. Key:
`subscription_id`.

| Column | Type | Meaning | Personal data | Notes |
|---|---|---|---|---|
| *(index)* | integer | Export row number | No | Not in the source table |
| `subscription_id` | integer | Subscription ID | No | 1 to 50,091 |
| `c_id` | varchar(40) | The subscriber, → `customer` | Yes · identifier | All 50,091 are buyers |
| `start_date` | date | First day | No | 2024-07-27 to 2025-07-27 |
| `end_date` | date | Last day | No | 2025-07-27 to 2026-07-27 |

## Addresses

### `shipping_details` · 200,001 rows

Delivery addresses. Each belongs to one customer, through
`customer_shipping`. Key: `address_id`.

| Column | Type | Meaning | Personal data | Notes |
|---|---|---|---|---|
| *(index)* | integer | Export row number | No | Not in the source table |
| `address_id` | integer | Address ID | No | 1 to 200,001 |
| `street_address` | varchar(100) | Street and number | Yes · contact | Synthetic street names in the country's language |
| `city` | varchar(100) | Town | Yes · location | Real town names (GeoNames) |
| `state` | varchar(100) | Region | Yes · location | Named after the original US schema. Holds European regions, 83 distinct |
| `zip` | varchar(10) | Postcode | Yes · location | **Text, not a number:** 19,622 start with `0`, and 12,630 contain letters (Dutch postcodes) |
| `country` | varchar(60) | Country | Yes · location | 6 values: Belgium, France, Germany, Italy, Netherlands, Spain. The country of the ML team's grain |
| `phone` | varchar(15) | Phone for delivery | Yes · contact | The customer's phone, repeated on each of their addresses. **Text:** 125,861 start with `0` |

### `customer_shipping` · 200,001 rows

Which customer has which address. Key: (`address_id`, `c_id`).

| Column | Type | Meaning | Personal data | Notes |
|---|---|---|---|---|
| *(index)* | integer | Export row number | No | Not in the source table |
| `address_id` | integer | → `shipping_details` | No | |
| `c_id` | varchar(40) | → `customer` | Yes · identifier | Only buyers have addresses |
| `is_default` | char(1) | `1` for the customer's default address, else `0` | No | Each buyer has 1, 2 or 3 addresses (33,219 / 33,561 / 33,220 buyers) and exactly one default |

## Payments

### `payment_details` · 100,000 rows

Saved payment cards. Each belongs to one buyer, through `customer_payment`.
Key: `payment_id`.

| Column | Type | Meaning | Personal data | Notes |
|---|---|---|---|---|
| *(index)* | integer | Export row number | No | Not in the source table |
| `payment_id` | integer | Card ID | No | 1 to 100,000. Referenced by `orders` and `payment` |
| `card_no` | bigint | Card number | **Yes · never ingest** | 11 to 19 digits. Synthetic |
| `cvv` | smallint | Card security code | **Yes · never ingest** | Stored after authorisation, which PCI DSS forbids. Lost its leading zeros: 961 have one digit, 8,440 have two |
| `expiry_date` | date | Card expiry | Yes · card | |
| `billing_address` | varchar(500) | Billing address | Yes · contact | The default shipping address, street, town, region and postcode glued together without separators |

### `customer_payment` · 100,000 rows

Which customer saved which card. Key: (`c_id`, `payment_id`).

| Column | Type | Meaning | Personal data | Notes |
|---|---|---|---|---|
| *(index)* | integer | Export row number | No | Not in the source table |
| `payment_id` | integer | → `payment_details` | No | |
| `c_id` | varchar(40) | → `customer` | Yes · identifier | |
| `is_default` | char(1) | `1` for the customer's default card | No | Always `1`: one card per buyer |

### `payment` · 222,644 rows

One transaction per order. Not in the original extract: **no index column.**
Key: `transaction_id`.

| Column | Type | Meaning | Personal data | Notes |
|---|---|---|---|---|
| `transaction_id` | integer | Transaction ID | No | 1 to 222,644 |
| `order_id` | integer | → `orders` | No | |
| `payment_id` | integer | The saved card used, → `payment_details`. Empty for a method without a card | No | Never empty in this export |
| `amount` | numeric(10,2) | Amount charged, in euros: the sum of the order's lines | No | Total €39,199,900.62, duplicate orders included |
| `method` | varchar(20) | Payment method | No | Always `Credit Card` |
| `status` | varchar(10) | Transaction status | No | Always `completed` |
| `created_at` | timestamp | When the payment was made | No | **No time zone.** 2023-09-15 00:32:26 to 2026-09-14 23:59:55 |

## Orders and deliveries

### `orders` · 222,644 rows

One row per order, placed by one buyer. It carries no product and no quantity:
those are in `order_items`. Key: `order_id`.

| Column | Type | Meaning | Personal data | Notes |
|---|---|---|---|---|
| *(index)* | integer | Export row number | No | Not in the source table |
| `order_id` | integer | Order ID | No | 1 to 222,644 |
| `buyer_id` | varchar(40) | → `buyer` | Yes · identifier | All 100,000 buyers have orders |
| `discount_id` | integer | → `discount` | No | **Empty on every row** |
| `payment_id` | integer | The saved card used, → `payment_details` | No | |
| `order_date` | date | Day the order was placed | No | A date with no time. 2023-09-15 to 2026-09-14, 1,096 days |

**Every order appears twice.** The twin has the same buyer, card and lines,
dated 0 to 4 days later (dataset card). The course's L04 demo uses
`order_id <= 111322` to keep the originals.

### `order_items` · 408,560 rows

One row per product in an order. Not in the original extract: **no index
column.** Key: (`order_id`, `p_id`).

| Column | Type | Meaning | Personal data | Notes |
|---|---|---|---|---|
| `order_id` | integer | → `orders` | No | |
| `p_id` | varchar(10) | → `product` | No | **Text:** 30 lines carry a `p_id` that starts with `0` |
| `qty` | integer | Units ordered | No | 1 to 12 |
| `price_at_purchase` | numeric(10,2) | Unit price paid, in euros, rounded to cents | No | 30 lines at 0.00: products priced under half a cent |

### `shipment` · 408,560 rows

One shipment per order line. Key: `shipping_id`.

| Column | Type | Meaning | Personal data | Notes |
|---|---|---|---|---|
| *(index)* | integer | Export row number | No | Not in the source table |
| `shipping_id` | integer | Shipment ID | No | 1 to 408,560 |
| `order_id` | integer | → `orders` | No | |
| `p_id` | varchar(10) | → `product` | No | |
| `carrier_id` | integer | → `carrier` | No | 1 to 4 |
| `shipment_type` | char(2) | Shipment type: the schema allows `PP` and `NP`, without saying what they mean | No | Always `NP` |
| `status` | varchar(10) | Delivery status | No | `delivered` 404,679, `in_transit` 2,807, `processing` 1,074. Set from the order's age when the export was made |
| `est_delivery_date` | date | Estimated delivery date | No | |
| `actual_delivery_date` | date | Actual delivery date | No | Empty for the 3,881 shipments not delivered yet |

### `carrier` · 4 rows

Delivery companies (fictional). Key: `carrier_id`.

| Column | Type | Meaning | Personal data | Notes |
|---|---|---|---|---|
| *(index)* | integer | Export row number | No | Not in the source table |
| `carrier_id` | integer | Carrier ID | No | 1 to 4 |
| `carrier_name` | varchar(30) | Name | No | Albatros Parcels, Blue Heron Logistics, Kestrel Freight, Swift Otter Delivery |

### `returns` · 0 rows

Returned products. **Empty in this export.** Key: `return_id`.

| Column | Type | Meaning | Personal data | Notes |
|---|---|---|---|---|
| *(index)* | integer | Export row number | No | Not in the source table |
| `return_id` | integer | Return ID | No | |
| `buyer_id` | varchar(40) | → `buyer` | Yes · identifier | |
| `p_id` | varchar(10) | → `product` | No | |
| `order_id` | integer | → `orders` | No | |

### `discount` · 0 rows

Discount codes an order can carry. **Empty in this export.** Key:
`discount_id`.

| Column | Type | Meaning | Personal data | Notes |
|---|---|---|---|---|
| *(index)* | integer | Export row number | No | Not in the source table |
| `discount_id` | integer | Discount ID | No | |
| `discount_name` | varchar(20) | Name | No | |
| `d_desc` | varchar(100) | Description | No | |
| `discount_amt` | numeric | Amount | No | |

### `daily_deals` · 0 rows

A product's discount on one day, applied at checkout by the
`APPLY_DAILY_DEALS` procedure. **Empty in this export.** Key: (`p_id`,
`deal_date`).

| Column | Type | Meaning | Personal data | Notes |
|---|---|---|---|---|
| *(index)* | integer | Export row number | No | Not in the source table |
| `p_id` | varchar(10) | → `product` | No | |
| `deal_date` | date | Day of the deal | No | |
| `discount` | numeric | Discount, in percent of the price | No | |

## Catalogue

### `product` · 42,858 rows

The catalogue, with current price and stock. Key: `p_id`.

| Column | Type | Meaning | Personal data | Notes |
|---|---|---|---|---|
| *(index)* | integer | Export row number | No | Not in the source table |
| `p_id` | varchar(10) | Product ID (an Amazon ASIN) | No | **Text, not a number:** 10 characters, 6 start with `0` (`0124784577`) |
| `p_name` | varchar(1000) | Product name | No | 6 empty |
| `p_desc` | varchar(5000) | Product details, as JSON whose fields vary by product | No | Semi-structured |
| `price` | numeric | Current catalogue price, in euros | No | 35,205 prices have more than two decimals. Lowest 0.00043 (5 round to 0.00), highest 2,143.46 |
| `qty` | integer | Units in stock | No | 1 to 100 |
| `category_id` | integer | → `category` | No | 1 or 2 |

### `category` · 2 rows

Key: `category_id`.

| Column | Type | Meaning | Personal data | Notes |
|---|---|---|---|---|
| *(index)* | integer | Export row number | No | Not in the source table |
| `category_id` | integer | Category ID | No | 1, 2 |
| `name` | varchar(30) | Name | No | `All Beauty`, `Premium Beauty` |
| `c_desc` | varchar(20) | Description | No | `beauty general`, `beauty premium` |

### `product_images` · 186,837 rows

Product photos, as links. Key: (`p_id`, `p_image`).

| Column | Type | Meaning | Personal data | Notes |
|---|---|---|---|---|
| *(index)* | integer | Export row number | No | Not in the source table |
| `p_id` | varchar(10) | → `product` | No | 37,041 products have images |
| `p_image` | varchar(100) | URL of the image on Amazon's image host | No | A link only: no image is stored |

### `seller_products` · 46,593 rows

Which seller sells which product. Key: (`seller_id`, `p_id`).

| Column | Type | Meaning | Personal data | Notes |
|---|---|---|---|---|
| *(index)* | integer | Export row number | No | Not in the source table |
| `seller_id` | varchar(40) | → `seller` | Yes · identifier | 16,997 sellers |
| `p_id` | varchar(10) | → `product` | No | Every product has at least one seller |

### `wishlist_item` · 24,810 rows

Products a buyer saved for later. Key: (`product_id`, `buyer_id`).

| Column | Type | Meaning | Personal data | Notes |
|---|---|---|---|---|
| *(index)* | integer | Export row number | No | Not in the source table |
| `product_id` | varchar(10) | → `product.p_id` | No | Named `product_id` here, `p_id` everywhere else |
| `buyer_id` | varchar(40) | → `buyer` | Yes · identifier | 19,823 buyers |

## Reviews

### `review` · 111,322 rows

Product reviews, written by buyers. The text is real (Amazon Reviews'23). Key:
`review_id`.

| Column | Type | Meaning | Personal data | Notes |
|---|---|---|---|---|
| *(index)* | integer | Export row number | No | Not in the source table |
| `review_id` | integer | Review ID | No | 96,001 to 207,322 |
| `buyer_id` | varchar(40) | → `buyer` | Yes · identifier | |
| `r_desc` | varchar(20000) | Review text | Unclassified | Up to 14,643 characters. 14 empty and 110 a single space: 124 blank after trimming. 13 are strings pandas reads as missing (`None`, `NA`, `N/A`) |
| `title` | varchar(300) | Review title | Unclassified | 21 are strings pandas reads as missing (`None`, `NA`, `N/A`, `n/a`) |
| `rating` | int | Stars | No | 1 to 5 |
| `seller_product_flag` | char(1) | Whether the review is about the seller (`S`) or the product (`P`) | No | Always `S`, although every review is linked to both a product and a seller |

### `product_reviews` · 111,322 rows

Which review is about which product. A bridge table: a product has many
reviews, so joining it to order lines multiplies them (L05). Key: (`p_id`,
`review_id`).

| Column | Type | Meaning | Personal data | Notes |
|---|---|---|---|---|
| *(index)* | integer | Export row number | No | Not in the source table |
| `p_id` | varchar(10) | → `product` | No | 41,323 products have reviews |
| `review_id` | integer | → `review` | No | |

### `seller_reviews` · 111,322 rows

Which review is about which seller. Key: (`seller_id`, `review_id`).

| Column | Type | Meaning | Personal data | Notes |
|---|---|---|---|---|
| *(index)* | integer | Export row number | No | Not in the source table |
| `seller_id` | varchar(40) | → `seller` | Yes · identifier | 16,604 sellers |
| `review_id` | integer | → `review` | No | |

### `review_images` · 119,382 rows

Images reviewers attached to their reviews, as links. Key: (`review_id`,
`review_img`).

| Column | Type | Meaning | Personal data | Notes |
|---|---|---|---|---|
| *(index)* | integer | Export row number | No | Not in the source table |
| `review_id` | integer | → `review` | No | 11,282 reviews have images |
| `review_img` | varchar(200) | URL of an image the reviewer uploaded | Unclassified | A link only. A photo a person took can show anything |

## Carts

### `cart` · 0 rows

A buyer's open shopping cart. Filled by the running shop, **empty in this
export.** Key: `cart_id`.

| Column | Type | Meaning | Personal data | Notes |
|---|---|---|---|---|
| *(index)* | integer | Export row number | No | Not in the source table |
| `cart_id` | integer | Cart ID | No | |
| `buyer_id` | varchar(40) | → `buyer` | Yes · identifier | |
| `total_qty` | int | Units in the cart | No | |
| `total_price` | float | Cart total | No | A float, not a decimal |

### `cart_items` · 0 rows

The products in a cart. **Empty in this export.** Key: (`cart_id`, `p_id`).

| Column | Type | Meaning | Personal data | Notes |
|---|---|---|---|---|
| *(index)* | integer | Export row number | No | Not in the source table |
| `cart_id` | integer | → `cart` | No | |
| `p_id` | varchar(10) | → `product` | No | |
| `qty` | integer | Units | No | |
