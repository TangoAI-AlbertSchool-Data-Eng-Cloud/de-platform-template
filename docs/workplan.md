# Work plan until session 5

**Goal:** project steps 1 to 4 done, reviewed and merged before session 5.
The deliverables and "done when" lines below come from the course brief.

How to work (setup, names, review rules): [CONTRIBUTING.md](../CONTRIBUTING.md).

**No service accounts, so full batch.** Charles told us (29 October) that
groups get no service accounts in this project. Without one, Airbyte cannot
reach our bucket or BigQuery, so the database tables reach bronze through our
own extractor, with full batch as its main mode. The next session shows a
workaround with Airflow.

## Who owns what

| Member | Owns | ADR | PRs reviewed by |
|---|---|---|---|
| **Till** | Steps 1 and 2, the extractor (full batch and incremental), data dictionary, `docs/architecture.md` | 0001 (done), 0002 | Jane |
| **Jane** | Step 3: the clickstream consumer, its schema and dead letter queue, failure modes | 0003 | Evaluna |
| **Enzo** | Step 4: native tables, tuning, materialised view, cost cap, runbook | 0004 | Jane |
| **Evaluna** | Tasks from session 5 on | | |

- **Step 2 moved from Evaluna to Till on 3 November.** Evaluna wrote the
  landing script (#10); her next tasks come with the later steps.
- **For now, Jane approves and merges Till's PRs.** For every other PR, the
  reviewer approves and the author merges.
- **Everyone:** write your role in the README team table, as a commit of your
  own on the branch `docs/team-roles` (#19). Jane merges it once all four
  rows are filled.
- At the defence, everyone is asked about an ADR they did not write.

## Till

**T1 · Step 1 and repo setup.** Done: #2 to #5, #7 and #8, merged on
22 October.

**T2 · Extractor:** `ingestion/extract_orders.py` (step 3, deliverable 2).
- Plain SQL through a database driver (`psycopg`), no ORM. Credentials come
  from `DATABASE_URL`. It writes to the bucket with the runner's own Google
  login: no key file.
- The table is a setting (`TABLE`), as in the L06 demo, so one script carries
  seven tables: `orders`, `order_items`, `review`, `product_reviews`,
  `product`, `customer_shipping`, `shipping_details`.
- Two modes:
  - **Full batch, the default:** re-reads the whole table on every run. It
    sees new rows, updates and deletes, and costs one full read per run,
    nothing at this size.
  - **Incremental,** as the brief asks: a cursor on `order_date` that survives
    a restart, reading only the rows past it.
- Selects columns by name, never `customer.pwd`, `payment_details.card_no` or
  `cvv`.
- Retries a failed connection with a growing delay, then gives up.
- Writes Parquet into a bronze prefix of its own: `land_export.py` deletes
  anything else under `bronze/<table>/`.

*Done when:* a full run matches the source's row count, a second incremental
run reads only new rows, and a stopped database gives retries, then a clean
failure. Record `>` versus `>=`, and what the incremental cursor misses that
the full batch sees, for ADR 0003.

**T3 · Connector: dropped.** Without a service account, Airbyte cannot write
to our bucket or BigQuery. T2's full batch carries the seven tables instead.

**T4 · Data dictionary** (step 2, deliverable 3). v1 merged (#8), the bronze
types in #17. Step 3 adds the extractor's and the consumer's paths.

**T5 · `docs/architecture.md`.** Step 2 is in #18. Still to add, last: step 3
(three arrows into bronze), step 4 (the native tables), a change-log row per
lesson, and ADRs 0003 and 0004 in the decisions table.

## Till: step 2, bronze

Every deliverable is in a pull request, for Jane to review and merge.

| Task | Deliverable | What | PR |
|---|---|---|---|
| T6 · Bucket and dataset | | `gs://data-engineering-i1-g04` (Evaluna, 22 October), `g04_bronze_1` (3 November), readable by the four of us | #12 |
| T7 · The export as partitioned Parquet | 1 | `ingestion/land_export.py`: 27 tables, without `pwd`, `card_no` and `cvv` | #10, #12 |
| T8 · ADR 0002 | 2 | `docs/adr/0002-bronze-layout.md` | #14 |
| T4 · Data dictionary v1 | 3 | `docs/data-dictionary.md` | #8, #17 |
| T9 · Lifecycle and access as files | 4 | `infra/lifecycle.json` (applied), `infra/iam.md` | #15 |
| T10 · Monthly cost | 5 | `docs/costs.md` | #16 |
| T5 · Updated diagram | 6 | `docs/architecture.md` | #18 |

- **Merge order:** #13 first, so that `main` has this plan, then #12, then
  #14 to #18. #18 links to #14 and #15.
- **Evaluna deletes the old dataset `g04_bronze`:** the dataset only. The
  bucket and its files stay.

*Done when* (the brief): partitioned Parquet and unmodified bronze, an ADR that
argues from our own measurements, a dictionary that marks all personal data,
infra files that match reality, costs that name prices and their date, a
diagram that shows the bucket, every member committed, at least one reviewed
PR.

## Jane: step 3, the stream

**J1 · Consumer:** `ingestion/consume_clickstream.py` (deliverable 3).
- Start from the course's `consume_clickstream.py` (L03, Exercise 1 page).
- It reads topic `clickstream` on `localhost:9092`.
- It writes partitioned Parquet to
  `gs://data-engineering-i1-g04/bronze/clickstream/`. Decide whether to
  partition by `event_time` or `emitted_at`, and say why. If the upload is
  refused, tell Till: our rights on the bucket come from course roles we
  cannot list.
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

Bronze is in `g04_bronze_1` (T7), readable by Enzo. Before any measurement,
turn the query cache off. Record **bytes processed**, never bytes billed:
billing has a 10 MiB minimum.

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

**N6 · Costs:** add the warehouse section to `docs/costs.md`, after #16 is
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

The seven tables the setup checks for are `g04_bronze_1`'s external tables.

## Not in this plan

- The Exercise 2 PDFs: each of us writes them after the project work.
- Till's L02 Exercise 1 page (PR #6).
