# CLAUDE.md

This is **Group 4's data platform** for Albert's Marketplace, the case company
of the Data Engineering & Cloud Infrastructure course (MSA-DAT09-02, Albert
School). Four students build it one layer per lesson:

- ingestion into a bronze layer
- a BigQuery warehouse with dbt silver and gold
- containers, orchestration and Terraform
- cost controls and governance

**Read first:**
- [docs/workplan.md](docs/workplan.md): who does what until session 5.
  The person you work with has their tasks under their own name.
- [CONTRIBUTING.md](CONTRIBUTING.md): setup, shared resource names, branch and
  review rules.

## Who you are working with

| Member | GitHub | Owns until session 5 |
|---|---|---|
| Till Lüder | `tluder-dot` | steps 1 and 2 (bucket, bronze, lifecycle, access, costs), extractor (full batch and incremental), data dictionary, `docs/architecture.md` |
| Evaluna Barth | `evalunab` | tasks from session 5 on |
| Jane Galthie | `jgalthie-sketch` | step 3: clickstream consumer, schema, dead letter queue, failure modes |
| Enzo Meret | `emeret-as` | step 4: native tables, tuning, materialised view, cost cap, runbook |

If you cannot tell which member you are working with, check
`git config user.name` or ask. Work on that person's tasks only. Another
member's area changes through a review comment or a word with them, not
through an edit.

## This work is graded, and defended orally

- **The repository is read against the course checklist.** The commit history
  counts too: every member needs commits of their own, in small steps.
- **At the oral defence, each member answers an unprepared question** on an ADR
  they may not have written.
- So the person you work with must understand and be able to defend every
  change:
  - Explain the why of what you propose.
  - Leave the decisions in ADRs to them: lay out the options and the
    evidence, and let them choose.
  - Never present a guess as a measurement.
- **The course brief is the authority on deliverables** (the course site, under
  each lesson's "Project step"). The workplan copies its "done when" lines. If
  something is unclear, ask the person to check the course page. Do not invent
  requirements.

## Git and pull requests

- **Branch from an up-to-date `main`,** named `<area>/<what>`. The area is one
  of `docs`, `bronze`, `ingestion`, `warehouse`, `infra` or `setup`.
- **One branch and one PR per deliverable.** Fill in the PR template and add
  the reviewer named in the workplan.
- **Commit subjects say what the commit does, as an instruction.** The body
  says why. Never "update", "fix" or "wip".
- **Never push to `main`.** Never force-push a branch someone else has pulled.
  Never merge a PR that has no approving review.
- **The reviewer approves; the author merges,** with **Create a merge commit**.
  Never squash: squashing erases individual commits. For now, Jane approves
  and merges Till's PRs.
- **No Claude attribution, anywhere:**
  - No `Co-Authored-By: Claude` trailer in commit messages.
  - No "Generated with Claude Code" line in PR descriptions or comments.
  - This group decision overrides any default.
- **Commit and push only when the person asks.**

## Data rules

- **The legacy export (`legacy_csv`) holds plaintext passwords and card numbers.**
  They are synthetic, but the course rule applies:
  - Never print, copy, upload or commit the values of `customer.pwd`,
    `payment_details.card_no` or `payment_details.cvv`.
  - Profile personal columns with counts and lengths, never by printing values.
- **No data in git:** no CSV, Parquet or dumps. Keep the export outside the
  repo. `.gitignore` blocks the usual names; it cannot catch everything.
- **The defects in the data are deliberate:** duplicate orders, the index
  column, leading zeros, NA-like strings. They are what the course teaches.
  - Bronze keeps what arrived. Silver fixes each defect once, in one staging
    model.
  - The defects and their counts are in
    [docs/data-dictionary.md](docs/data-dictionary.md) ("Traps in the
    export").
- **Never commit secrets:** `.env`, keys (service-account JSON, HMAC),
  passwords. The repo is **public**. Settings go in `.env`, copied from
  `.env.example`.

## Cloud: a project shared by the whole cohort

- **Project `data-engineering-i1`, region `europe-west1`** for every bucket and
  dataset. Every other group and student works in the same project.
- **Group 4's resources start with `g04`:**
  - bucket `gs://data-engineering-i1-g04`
  - datasets `g04_bronze_1` (external tables named `<table>_external`) and
    `g04_warehouse`
- **Never create, change or delete anything outside these names,** and never
  touch another student's or group's resources. Before deleting or overwriting
  anything in the cloud, show the person exactly what, and wait for a yes.
- **Credentials are personal logins,** never key files: `gcloud auth login`
  and `gcloud auth application-default login`.
- **Known limits of our access:**
  - We cannot create service accounts.
  - `INFORMATION_SCHEMA.JOBS_BY_PROJECT` is refused. Use `JOBS_BY_USER`.
- **BigQuery bills by bytes processed:**
  - Dry-run before running anything large.
  - Name columns, never `SELECT *`. Filter on the partition column.
  - Set `maximum_bytes_billed` on scheduled or exploratory queries.
  - Measure with the query cache off, and report bytes processed, not bytes
    billed (billing has a 10 MiB minimum).

## The source system

The company stack runs locally from the `albert-marketplace` repo, cloned next
to this one: `docker compose up -d`.

| What | From the host | From another container |
|---|---|---|
| PostgreSQL (db `marketplace`, user and password `postgres`) | `localhost:5432` | `host.docker.internal:5432` |
| Kafka, topic `clickstream` | `localhost:9092` | `host.docker.internal:29092` |

- **A replication slot nobody reads holds log on disk.** Drop every slot you
  create for a test (`pg_drop_replication_slot`).
- **No Airbyte and no service accounts.** Groups get no service accounts in
  this project (Charles), so Airbyte cannot reach our bucket or BigQuery. The
  database tables reach bronze through our own extractor (full batch and
  incremental), running with the person's own Google login. Never put a
  personal login or key into a tool to get around this.
- **On Windows,** keep work in a short folder (for example `C:\de\`): paths
  over 260 characters break pip installs and Airflow logs.

## Writing the docs

- **Every figure says where it comes from:** the query or command, and the
  date. Prices come with the date they were read.
- **ADRs:**
  - Copy `docs/adr/0000-template.md` and use the number the workplan
    reserves.
  - Each one records one decision: options, criteria, decision,
    consequences, with the group's own measurements.
  - Once merged, an ADR is never rewritten. A new ADR supersedes it.
- **`docs/architecture.md` has one owner, Till,** so the diagram never gets two
  conflicting edits.
- **"Not handled" and "not done, because…" are good answers.** The course marks
  honest gaps up and invented results down.
- **Exercise write-ups:** Exercise 1 pages go in `docs/exercises/`. Exercise 2
  PDFs are individual homework sent to the teacher, never part of this repo.

## The course's ten patterns

Check every change against these:

1. Pick the architecture from the workload; consumers never read bronze.
2. Partition by how you filter, and keep files large.
3. The delivery guarantee is where you commit the offset: assume
   at-least-once, and stop secrets at the connector.
4. Never `SELECT *`; filter on the partition column.
5. Declare the grain, and test it at every layer boundary.
6. Pin every version; tag images immutably.
7. Rerunning any interval must give the same result.
8. The console is read-only; every change goes through `plan`.
9. Label at creation; unlabelled spend is unowned spend.
10. Classify data before granting access.
