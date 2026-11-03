# How we work on this repo

Read this once before your first change. [docs/workplan.md](docs/workplan.md)
says who does what until session 5.

## 1. Set up your machine (once, about 30 minutes)

1. **Clone this repo:**

   ```
   git clone https://github.com/tluder-dot/DataEnGroup4.git
   cd DataEnGroup4
   ```

2. **Google Cloud.** Everything runs in the course project
   `data-engineering-i1`, region `europe-west1`:

   ```
   gcloud auth login
   gcloud config set project data-engineering-i1
   gcloud auth application-default login
   gcloud auth application-default set-quota-project data-engineering-i1
   ```

   The last two lines let Python, dbt and later Terraform act as you without a
   key file. Rerun them whenever a tool says your credentials expired.

3. **Python 3.12 or later, in a virtual environment** (L02 setup), with
   `pandas` and `pyarrow`. For ingestion work, also `confluent-kafka` and
   `psycopg[binary]`. Each job pins its exact versions in its own folder.

4. **The company stack** (L03 setup). Clone it **next to** this repo, not
   inside it:

   ```
   git clone https://github.com/TangoAI-AlbertSchool-Data-Eng-Cloud/albert-marketplace.git
   cd albert-marketplace
   docker compose up -d
   ```

   | What | From your machine | From another container |
   |---|---|---|
   | PostgreSQL (db `marketplace`, user and password `postgres`) | `localhost:5432` | `host.docker.internal:5432` |
   | Kafka, topic `clickstream` | `localhost:9092` | `host.docker.internal:29092` |

   If Docker Desktop restarts, the database and Kafka stop: run
   `docker compose up -d` again.

5. **The export** (`legacy_csv.tar.gz`, release v1.0.0). Keep it **outside**
   this repo. `customer.csv` and `payment_details.csv` hold plaintext
   passwords and card numbers. They are synthetic, but the course rule
   applies: never copy, screenshot or upload those columns.

6. **Your own settings:** `cp .env.example .env`. The values in it are
   already ours. `.env` is never committed.

## 2. Shared resources

`data-engineering-i1` is shared by **the whole cohort**, so every resource
the group owns starts with `g04`: we are group 4. The buckets and datasets
from your exercises stay personal: never write group data there, and never
write into anyone else's.

| What | Name | Owner |
|---|---|---|
| Group bucket | `gs://data-engineering-i1-g04` | Till (L02) |
| Bronze, one prefix per table | `gs://data-engineering-i1-g04/bronze/<table>/` | Till (export, extractor), Jane (clickstream) |
| Dead letter queue | `gs://data-engineering-i1-g04/bronze/_dlq/<source>/` | Jane (L03) |
| BigQuery: bronze as external tables | dataset `g04_bronze_1`, tables `<table>_external` | Till (L02) |
| BigQuery: native tables | dataset `g04_warehouse` | Enzo (L04) |

- **Region:** `europe-west1` for every bucket and dataset. Location is fixed
  when a bucket or dataset is created, and moving one means recreating it.
- **External tables are named `<table>_external`.** That is the name L05's dbt
  sources expect.

## 3. Every change: branch, commit, pull request, review

1. **Branch from an up-to-date `main`:**

   ```
   git switch main
   git pull
   git switch -c bronze/landing
   ```

   Name branches `<area>/<what>`. The area is one of `docs`, `bronze`,
   `ingestion`, `warehouse`, `infra` or `setup`.

2. **Commit in small steps.** The history is graded. The subject says what
   the commit does, as an instruction: *"Partition bronze orders by order
   date"*. When the reason is not obvious, the body says why. Never "update",
   "fix" or "wip".

3. **Push and open a pull request early,** as a draft while unfinished. Fill
   in the template and add the reviewer named in the work plan.

4. **The reviewer checks the content, not just the format.** Rerun a query,
   open a file, compare a figure with its source. Then submit a GitHub review:
   **Approve**, or **Request changes** with comments. A merge without a
   submitted review does not count as reviewed.

5. **The author merges after approval,** with **Create a merge commit**. Never
   squash: squashing replaces our individual commits with one. Then delete the
   branch.

6. **Never push to `main`,** and never merge your own pull request without an
   approval.

## 4. What never goes into git

- `.env`, keys (service-account JSON, HMAC keys), passwords (Airbyte, Docker
  Hub, databases).
- Data: CSV, Parquet, dumps.
- Terraform state (from L08).

A secret pushed once stays in the history even after the file is deleted. If
it happens, tell the group and rotate the secret: the repo is **public**.

## 5. Writing the docs

- **Every figure says where it comes from:** the query or command, and the
  date. Prices come with the date you read them. BigQuery figures are bytes
  processed with the query cache off, never bytes billed.
- **ADRs:** copy `docs/adr/0000-template.md`. Use the number the work plan
  reserves for you. One decision per ADR. Once merged, an ADR is never
  rewritten: a new ADR supersedes it.
- **`docs/architecture.md` has one owner, Till,** so its diagram never gets two
  conflicting edits. Tell him what changed in your area, or comment on his PR.
- **"Not handled" and "not done, because…" are good answers.** A guess written
  as a fact is not.
