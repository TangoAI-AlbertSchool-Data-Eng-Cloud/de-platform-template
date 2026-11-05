# ADR-0002: Land bronze as snappy Parquet, one folder per table, orders partitioned by year

- **Status:** accepted
- **Date:** 2026-11-03
- **Author:** Till Lüder
- **Lesson:** L02

## Context

Bronze is the first copy of the company's data on the platform, in
`gs://data-engineering-i1-g04/bronze/` (`europe-west1`), read through the
external tables in `g04_bronze_1`. The brief asks for partitioned Parquet with
a key of our choice, and for bronze to hold what arrived: no cleaning, no
deduplication, no dropped columns.

| Fact | Figure | Source |
|---|---|---|
| The export | 27 tables, 197 MiB of CSV. The biggest have 408,560 rows (`order_items`, `shipment`) | ADR-0001 |
| Dates | The reports filter on `orders.order_date`: 1,096 days, 15 Sep 2023 to 14 Sep 2026. `payment` and `shipment` have dates of their own; `order_items` has none | Data dictionary |
| File sizes as Parquet | 30 files, 104 MB in all; the biggest is `review` (18 MB) | `gcloud storage objects list`, 3 November |
| How bronze is read | Whole tables (the warehouse load in step 4, dbt in L05) and orders by date (daily demand, revenue per month) | Work plan, star sketch |
| CSV against Parquet | `order_items`: 10,373,925 bytes as CSV, 3,546,854 as snappy Parquet (2.92×) | Exercise 1 (#6) |
| Too many partitions | One month by day and product against by day: 279× the objects, 88× the bytes, 3.7× slower (1,114 ms against 300 ms), the same bytes processed (17,056) | Exercise 1 (#6) |
| Orders by month | 37 files, median 180 KB | Evaluna, 22 October (commit `638b074`) |
| pandas' defaults | Drop leading zeros (82,203 customer phones, 30 order lines' `p_id`) and turn `NA`, `N/A`, `NULL` into nulls | Data dictionary, traps 2 and 4 |
| The secrets | `customer.pwd`, `payment_details.card_no` and `cvv` are never extracted | ADR-0001 |

## Options considered

| Option | For | Against |
|---|---|---|
| **Partition `orders` by year** of `order_date` | 4 files of 0.9 to 3.3 MB. A query on one year reads one file | A filter inside one year still reads the whole year |
| **By month** | Matches the reports' grain | 37 files of about 180 KB: small files cost operations and time, and save no bytes at this size |
| **By day** | Matches the daily demand grain | 1,096 files, one per day. In Exercise 1 a day of order lines was 12 KB, and more files cost time and saved no bytes |
| **No partitions** | One file, simplest | The brief asks for partitions. Every query reads all three years |
| **zstd instead of snappy** | Smaller files | Not measured. snappy is pyarrow's default, and the files are already small |
| **CSV** | Exactly what arrived, no conversion | 2.92× the bytes. Every query reads every column, and every reader guesses the types again |
| **Read with pandas' defaults** | No code | Changes the data on the way in (leading zeros, `NA`) |
| **Land the secret columns** | Bronze unchanged, as the brief says | ADR-0001 and PCI DSS: a CVV must not be stored. A column filtered later is already in bronze |
| **Skip `customer` and `payment_details`** (the first version, #10) | No secret can leak | Drops names, emails, phones and billing addresses too: far more than the brief allows |

## Criteria

- **File size:** files of megabytes, not kilobytes. Operations are billed per
  file ([costs](../costs.md)), and Exercise 1 showed small files only cost.
- **How bronze is read:** whole tables, and orders by date.
- **Unchanged:** every value as in the CSV, checked value by value.
- **Secrets stop at the boundary:** a column that is never read cannot leak.

## Decision

Bronze is snappy Parquet, one folder per table (`bronze/<table>/`). `orders` is
partitioned by year (`order_year=YYYY`). Every other table is one file: none
is bigger than 18 MB, and they are read whole. Every
column is read as text, and only the columns that are numbers or dates in every
file are cast. `pwd`, `card_no` and `cvv` are never read; everything else lands
as it arrived, with the index column kept as `csv_index`.

## Consequences

- **Cheap:** 30 files for 27 tables, so operations cost almost nothing. A
  rerun uploads only the files whose content changed. Filtering on
  `order_year` reads only that year's file.
- **Awkward:** a query must filter on `order_year`, not only `order_date`, to
  skip files. `order_items` has no date, so it cannot be partitioned without
  joining `orders` (step 4 does). Most columns are `STRING` in bronze, so
  silver does the casting. The bytes depend on the pyarrow version: Evaluna's
  26.0.0 and Till's 25.0.1 wrote different files for the same data.
- **Watch:** the extractor (step 3) lands the database tables every run. If it
  appends orders every day, a yearly folder collects many small files, and the
  key needs a new decision.
- **Forces a rewrite:** changing the key. The paths are in the external tables
  and, from L05, in the dbt sources.
