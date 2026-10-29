# Work plan until session 5

**Goal:** project steps 1 to 4 complete, reviewed and merged by **Sunday
25 October, 20:00**. Steps 2 and 3 are already late. Step 4 is due before
session 5. The deliverables and "done when" lines below come from the course
brief.

How to work (setup, names, review rules): [CONTRIBUTING.md](../CONTRIBUTING.md).

**No service accounts, so full batch.** Charles told us (recorded 29 October)
that groups get no service accounts in this project. Without one, Airbyte
cannot reach our bucket or BigQuery, so there is no connector: the database
tables reach bronze through our own extractor, with full batch as its main
mode. The next session shows a workaround with Airflow. This changes T2 and T3
below, and what ADR 0003, the failure modes and `iam.md` have to say.

## Who owns what

| Member | Owns | ADR | Reviews the PRs of |
|---|---|---|---|
| **Till** | Step 1, repo setup, batch ingestion (the extractor: full batch and incremental), data dictionary, `docs/architecture.md` | 0001 (done) | Evaluna |
| **Evaluna** | Step 2: group bucket, bronze, lifecycle, access, costs | 0002 bronze layout | Jane |
| **Jane** | Step 3: the clickstream consumer, its schema and dead letter queue, failure modes | 0003 ingestion modes | Enzo |
| **Enzo** | Step 4: native tables, tuning, materialised view, cost cap, runbook | 0004 warehouse pricing | Till |

Reviews go round in a circle, so each of us reads one other area closely. At
the defence, everyone is asked about an ADR they did not write.

## Timeline

| When | What |
|---|---|
| **Wed 21 Oct** | **Everyone:** set up your machine (CONTRIBUTING.md §1), review your step 1 PR(s) below, and make your first commit: your role in the README team table. **Evaluna:** create the bucket and the dataset (E1) and post in the group when they exist |
| **Thu 22 Oct** | **Evaluna:** bronze landed, with external tables over the seven tables (E2). Enzo's work depends on it, so it comes first |
| **Sat 24 Oct, 20:00** | Every PR open and ready for review |
| **Sun 25 Oct, 20:00** | Everything reviewed and merged. Till updates `docs/architecture.md` last |
| **Before session 5** | **Everyone, alone:** the L05 setup (bottom of this page) |

### Step 1 reviews: done

#2, #3, #4, #5 and #7, and the data dictionary (#8), were reviewed and merged
on 22 October. `main` now holds step 1, this plan and the rules, so everyone
can start their own tasks.

## Till

**T1 · Step 1 and repo setup.** Fixes to PRs #2 to #5, CONTRIBUTING.md, this
plan.
*Done when:* PRs #2 to #5 and #7 are merged after review, and every member
has a commit on `main`.

**T2 · Extractor:** `ingestion/extract_orders.py` (step 3, deliverable 2; it
also replaces the connector of deliverable 1).
- Plain SQL through a database driver (`psycopg`), no ORM. Credentials come
  from `DATABASE_URL`. It writes to the bucket with the runner's own Google
  login: no key file.
- The table is a setting (`TABLE`), as in the L06 demo, so one script carries
  the seven tables the connector would have: `orders`, `order_items`,
  `review`, `product_reviews`, `product`, `customer_shipping`,
  `shipping_details`.
- Two modes:
  - **Full batch, the default:** re-reads the whole table on every run. It
    sees new rows, updates and deletes, and costs one full read per run,
    nothing at this size.
  - **Incremental,** as the brief asks: a cursor on `order_date` that survives
    a restart, reading only the rows past it.
- Selects columns by name, never `customer.pwd`, `payment_details.card_no` or
  `cvv`.
- Retries a failed connection with a growing delay, then gives up.
- Writes Parquet into a bronze prefix of its own, agreed with Evaluna: her
  `land_export.py` deletes anything else under `bronze/<table>/`.

*Done when:* a full run matches the source's row count, a second incremental
run reads only new rows, and a stopped database gives retries, then a clean
failure. Record `>` versus `>=`, and what the incremental cursor misses that
the full batch sees, for ADR 0003.

**T3 · Connector: dropped.** With no service account, Airbyte cannot write
to our bucket or BigQuery (Charles). T2's full batch carries the seven tables
instead. The decision and its reason go into Jane's ADR 0003, as a rejected
option, and into the failure-modes document.

**T4 · Data dictionary v1:** `docs/data-dictionary.md` (step 2,
deliverable 3).
- Every landed table and every column: name, type, meaning, and whether it is
  personal data. Mark the names, emails, addresses and phones, the legacy
  passwords and the card data.
- Say which path each table came from (the export, the extractor, the
  clickstream consumer), and which columns each path adds.

*Done when:* column names and types match what Evaluna landed.

**T5 · `docs/architecture.md`, steps 2 to 4.**
- Step 2: the bucket, region, layout and who can read it.
- Step 3: three arrows into bronze.
- Step 4: the native tables.
- One change-log row per lesson, and ADRs 0002 to 0004 in the decisions
  table.

## Evaluna: step 2, bronze

**E1 · Bucket and dataset (Wednesday, first).**

```
gcloud storage buckets create gs://data-engineering-i1-g04 --location=europe-west1 --uniform-bucket-level-access
```

Then, in the BigQuery console: create the dataset `g04_bronze`, location
`europe-west1`. Post in the group when both exist.

**E2 · The export as partitioned Parquet** (step 2, deliverable 1).
- Commit the script that does it, `ingestion/land_export.py`, so it can be
  rerun.
- Files go to `gs://data-engineering-i1-g04/bronze/<table>/`.
- Bronze holds what arrived, unchanged: no cleaning, no deduplication, no
  dropped rows.
- Pandas' defaults change data on the way in. A phone number loses its
  leading zero, and the strings `None`, `NA`, `N/A` and `NULL` become nulls.
  Decide how you read types, and say so in ADR 0002.
- Two decisions to argue in ADR 0002:
  - **The partition key, per table.** `order_items` has no date column, and
    small tables may need no partitions at all.
  - **The secret columns.** The brief says bronze is unchanged, but ADR-0001
    says `customer.pwd`, `payment_details.card_no` and `cvv` are never
    extracted. Choose, and justify the choice.
- External tables `g04_bronze.<table>_external` (`WITH PARTITION COLUMNS`),
  at least for the seven tables listed in T2.

*Done when:* `COUNT(*)` on the external tables matches the export, for
example 222,644 orders and 408,560 order lines.

**E3 · ADR 0002:** `docs/adr/0002-bronze-layout.md`.
- **Decision:** partition key, format, codec.
- **Options:** at least one other key, and CSV.
- **Evidence:** Exercise 1 numbers, yours or Till's (PR #6): 279× more
  objects, 88× more bytes, 3.7× slower, the same bytes processed.
- **Consequences:** what is cheap, what is awkward, what would force a
  rewrite.

**E4 · Lifecycle and access as files:** `infra/lifecycle.json` and
`infra/iam.md`.
- `lifecycle.json` is the policy actually applied to the group bucket, with
  no delete rule, and the reason why:
  `gcloud storage buckets update gs://data-engineering-i1-g04 --lifecycle-file=infra/lifecycle.json`
- `iam.md` lists every binding on the bucket and the dataset: principal, role,
  scope, and a one-line reason. Copy it from reality:
  `gcloud storage buckets get-iam-policy gs://data-engineering-i1-g04`.
  We cannot create service accounts, and Charles confirmed we will not get
  one: every job runs as one of our personal logins. Say so.

*Done when:* both files match `gcloud storage buckets describe` and
`get-iam-policy`.

**E5 · Costs:** `docs/costs.md`.
- Monthly cost from published prices, with the date you read them: storage,
  operations (from your object count), and what changes at 100 times the data.
- Others extend it in later steps.

## Jane: step 3, the stream

**J1 · Consumer:** `ingestion/consume_clickstream.py` (deliverable 3).
- Start from the course's `consume_clickstream.py` (L03, Exercise 1 page).
- It reads topic `clickstream` on `localhost:9092`.
- It writes partitioned Parquet to
  `gs://data-engineering-i1-g04/bronze/clickstream/`. Decide whether to
  partition by `event_time` or `emitted_at`, and say why.
- The docstring states the delivery guarantee in one sentence, and the code
  matches it. For example, the offset is committed after the file is written:
  at least once.

**J2 · Schema and dead letter queue:** `ingestion/clickstream.schema.json`
(deliverables 4 and 5).
- A JSON Schema for the event: `schema_version`, `event_id`, `event_type`,
  `event_time`, `emitted_at`, `session_id`, `buyer_id`, `p_id`, `qty`.
- The consumer validates each event before accepting it, and
  `schema_version` picks the schema.
- Failed events go to `bronze/_dlq/clickstream/` with the row, the reason and
  the time. One bad row must not stop the flow.

*Done when:* a deliberately broken event, sent with
`kafka-console-producer.sh`, sits in `_dlq/` and the consumer kept running.

**J3 · The evidence** (L03 Exercise 1, steps A and B).
- Kill the consumer between the write and the commit, restart it, then count
  rows against distinct `event_id`: that gives the duplicate count.
- CDC: create a slot, insert, update and delete a test product, peek at the
  changes, note the slot size, then **drop the slot**. An unread slot holds
  log on disk. Note which change an `order_date` cursor misses.

**J4 · Failure modes:** `docs/ingestion-failure-modes.md` (deliverable 6).
- A table: failure, handled?, by what, what happens.
- It covers at least: new rows, updates, deletes, source down, malformed row,
  schema change, duplicate after restart, expiring credential.
- It says where credentials live: our personal Google logins and a local
  `DATABASE_URL`, no service account (Charles). A login that expires stops the
  pipeline: that is the "expiring credential" row.
- At least one honest "not handled".

**J5 · ADR 0003:** `docs/adr/0003-ingestion-modes.md` (deliverable 7).
- The mode per source (the database tables, the clickstream).
- For the database tables: full batch by default, incremental as the second
  mode (T2).
- At least one rejected option. Airbyte with CDC is one: without a service
  account, it cannot reach our bucket or BigQuery (Charles).
- Evidence from J3 and from Till's extractor.
- The guarantee committed to, and what would force a change.

**J6 · Clickstream in the data dictionary** (deliverable 8), once T4 is
merged. Every field: type, meaning, and whether it is personal data. Answer
it for `buyer_id` and `session_id`.

## Enzo: step 4, the warehouse

Needs E2 (bronze as external tables). Until then, read the L04 lecture and
draft the queries. Before any measurement, turn the query cache off. Record
**bytes processed**, never bytes billed: billing has a 10 MiB minimum.

**N1 · The working set as native tables:** dataset `g04_warehouse`
(deliverable 1).
- Load the seven tables. `order_items` joins `orders` to get `order_date`.
- Say which tables you loaded and which stay external, and why.

**N2 · Tuning:** `docs/warehouse-tuning.md` (deliverables 2, 4 and 7).
- A table: table, change, query, bytes before, bytes after, ratio.
- Partition by a defended grain: three years of orders suggest month.
  Cluster where a query filters. Report the changes that bought nothing
  (1.0×) too, each with a sentence.
- Three analytical queries the project needs: SQL, bytes processed, cost at
  $7.50 per TiB, tuned versus untuned.
- `maximum_bytes_billed`: where it is set, the value and why, and the exact
  error it gives.

**N3 · Daily demand materialised view:** `warehouse/daily_demand.sql`
(deliverable 3), plus the collapse ratio, order lines ÷ distinct (product,
day), in N2's document. At about 1.14 the view saves no bytes under
per-byte billing. Keep it and say what it costs, or show a coarser grain that
moves the ratio.

**N4 · ADR 0004:** `docs/adr/0004-warehouse-pricing.md` (deliverable 5).
- On demand or capacity: the workload in numbers, and the crossover
  arithmetic.
- The decision and its cost.
- What would change your mind, as a number someone can watch.

**N5 · Runbook:** `docs/runbooks/slow-query.md` (deliverable 6).
- "A 2-second query now takes 2 minutes", written for a teammate at 23:00.
- Ordered steps, where to click, and when to escalate.
- It covers: lost partition filter, table outgrew its grain, one stage
  dominates, skew, data changed shape, cached comparison.

**N6 · Costs:** add the warehouse section to `docs/costs.md`, after E5 is
merged.

## Everyone, alone, before session 5: the L05 setup

About 20 minutes; the course's "Before the session: Docker and dbt" page.

1. Start Docker Desktop.
2. `docker pull charlestng/dbt-bigquery:1.12.1`
3. `gcloud auth application-default login`
4. In a folder outside this repo (`~/de/l05`), write `profiles.yml`
   (project `data-engineering-i1`, dataset `l05_<your initials>`, location
   `europe-west1`) and `dbt_project.yml`.
5. Run `dbt debug` in the container until it prints **All checks passed!**

The seven tables the setup checks for are `g04_bronze`'s external tables.

## Not in this plan

- The Exercise 2 PDFs: each of us writes them after the project work.
- Till's L02 Exercise 1 page (PR #6).
