#!/usr/bin/env bash
# Uploads locally-generated synthetic data to S3's raw/ zone.
# Plays the role of "the source system delivering export files" -
# intentionally separate from anything Spark/Databricks related.
set -euo pipefail

BUCKET="fitnesspulse-lakehouse-403322446403"
LOCAL_DIR="data/raw"
S3_DEST="s3://${BUCKET}/raw"

if [ ! -d "$LOCAL_DIR" ]; then
    echo "Error: $LOCAL_DIR does not exist. Run the generator first:"
    echo "  python -m src.generators.generate"
    exit 1
fi

echo "Syncing ${LOCAL_DIR}/ -> ${S3_DEST}/ ..."
aws s3 sync "$LOCAL_DIR" "$S3_DEST" --exclude "*.DS_Store"
echo "Done."