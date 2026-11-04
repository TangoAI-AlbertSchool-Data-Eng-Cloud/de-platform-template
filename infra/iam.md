# Access

Every binding on the group's bucket and bronze dataset, copied from
`gcloud storage buckets get-iam-policy gs://data-engineering-i1-g04` and
`bq show --format=prettyjson data-engineering-i1:g04_bronze_1` on
3 November 2026.

**There is no service account.** Groups get none in this project (Charles), so
every job runs as one of our personal Google logins.

## Bucket `gs://data-engineering-i1-g04`

Uniform bucket-level access, so there are no per-object permissions. The
bucket has only the bindings Cloud Storage gives every new bucket. We added
none.

| Principal | Role | Scope | Why |
|---|---|---|---|
| `projectOwner:data-engineering-i1` | `roles/storage.legacyBucketOwner`, `roles/storage.legacyObjectOwner` | Bucket | Default: the project's owners manage every bucket |
| `projectEditor:data-engineering-i1` | `roles/storage.legacyBucketOwner`, `roles/storage.legacyObjectOwner` | Bucket | Default: the project's editors can write and delete |
| `projectViewer:data-engineering-i1` | `roles/storage.legacyBucketReader`, `roles/storage.legacyObjectReader` | Bucket | Default: the project's viewers can list and read the files |

Our own logins get their rights from roles the course set on the project. We
cannot list them: `gcloud projects get-iam-policy` is refused. What Till's
login could do: create a bucket (L02 Exercise 1) and this dataset, write
objects, apply the lifecycle rule. What it could not: create a service
account.

## Dataset `g04_bronze_1`

| Principal | Role | Scope | Why |
|---|---|---|---|
| `projectOwners` | Owner | Dataset | Default, kept: the project's owners |
| Till | Owner | Dataset | Created the dataset and runs the landing script |
| Evaluna, Jane, Enzo | `roles/bigquery.dataViewer` | Dataset | Read bronze to build the warehouse (L04) and the dbt models (L05) |

`projectReaders` and `projectWriters`, which BigQuery adds to every new
dataset, were removed on 3 November. Bronze holds names, addresses and phone
numbers ([data dictionary](../docs/data-dictionary.md)), so only named people
read it.

How it was set:

```
bq --location=europe-west1 query --nouse_legacy_sql \
  'GRANT `roles/bigquery.dataViewer` ON SCHEMA `data-engineering-i1`.g04_bronze_1
   TO "user:<member>@albertschool.com", ...'
bq show --format=prettyjson data-engineering-i1:g04_bronze_1 > access.json
# delete the projectReaders and projectWriters entries from "access", then:
bq update --source access.json data-engineering-i1:g04_bronze_1
```

## Not handled

- **Anyone with Viewer on the project can read the bronze files** through the
  bucket's `projectViewer` binding, without access to the dataset. We cannot
  see who holds Viewer, so we do not know whether removing it would also cut
  off our own reads. It stays until L10 tightens access.
