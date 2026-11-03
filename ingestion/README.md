# Ingestion

Arrives in **L03 · Batch, streaming, CDC**: the pipelines that bring Albert's
Marketplace's data into the bronze layer.

In **L06** each ingestion job gets its Dockerfile here.

## The legacy export: `land_export.py`

Lands 25 of the 27 CSV files in `gs://data-engineering-i1-g04/bronze/<table>/`
as Parquet, and creates the external tables `g04_bronze_1.<table>_external`.
`customer` and `payment_details` are skipped: they hold the passwords and card
numbers.

The dataset was created once, with:

```
bq --location=europe-west1 mk --dataset --label=group:g04 --label=layer:bronze data-engineering-i1:g04_bronze_1
```

To rerun the landing (pandas and pyarrow, and your own `gcloud` login):

```
python ingestion/land_export.py --src <folder of the CSV files> --upload --external
```

If `gcloud storage rsync` stops with `gcloud-crc32c: command not found`, run
`gcloud components install gcloud-crc32c` once.
