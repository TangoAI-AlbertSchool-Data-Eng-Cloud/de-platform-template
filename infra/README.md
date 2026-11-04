# Infrastructure

Arrives in **L08 · Terraform**: your group's cloud resources declared as code,
with remote state and `terraform plan` running on every pull request.

- **Before L08,** the resources you create by hand in L02-L07 are listed in
  `docs/`.
- **From L08,** changes go through code, not the console.
- **L09** adds labels and budgets; **L10** tightens access.

## Applied by hand so far

| File | What | Applied with |
|---|---|---|
| [lifecycle.json](lifecycle.json) | The group bucket's lifecycle rule | `gcloud storage buckets update gs://data-engineering-i1-g04 --lifecycle-file=infra/lifecycle.json` |
| [iam.md](iam.md) | Every binding on the bucket and on `g04_bronze_1` | The commands in the file |

Check that both still match:

```
gcloud storage buckets describe gs://data-engineering-i1-g04 --format="value(lifecycle_config)"
gcloud storage buckets get-iam-policy gs://data-engineering-i1-g04
bq show --format=prettyjson data-engineering-i1:g04_bronze_1
```

## The lifecycle rule

Applied on 3 November 2026. Files under `bronze/` move to Nearline at 30 days,
Coldline at 90 and Archive at 365.

- **Why these ages:** the export is read when it is loaded into the warehouse
  and when the warehouse is rebuilt. After that it is cold. The extractor's
  full-batch files are replaced at every run, so they never reach 30 days.
- **Why no delete rule:** bronze promises that nothing that arrived is lost.
  The bucket's soft delete (the default, 7 days) also keeps an overwritten or
  deleted file for a week.
- **What to watch:** a job that reads files older than 30 days. Nearline saves
  $0.010 per GiB-month and charges $0.010 per GiB read, so reading a file more
  than once a month costs more than the class saves ([costs](../docs/costs.md)).
