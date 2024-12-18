# Local Object Store

## TL;DR

```
export AWS_ACCESS_KEY_ID=AWSACCESSKEYID
export AWS_SECRET_ACCESS_KEY=AWSSECRETACCESSKEY
export AWS_ENDPOINT_URL=http://localhost:9000

docker compose up -d

# list buckets (no buckets)
aws s3api list-buckets

# Make buckets
aws s3api create-bucket --bucket alerts
aws s3api create-bucket --bucket schema

# Add objects
aws s3 cp <alert_file> s3://alerts/
aws s3 cp <schema_file> s3://schema/
```

## Prereqs

- AWS CLI tool (`brew install awscli`)
- Docker

## How

- Minio is an object store server that provides the same API as Amazon S3, so it
  can be used as a drop-in replacement for S3 and other compatible object stores.

- The AWS credentials (AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY) map to minio
  settings for `MINIO_ROOT_USER` and `MINIO_ROOT_PASSWORD`

- The `AWS_ENDPOINT_URL` variable tells *all* AWS API tools where to send their
  commands -- this includes the aws cli tool and `boto3`!

- Use standard AWS CLI tools to create buckets and add data to Minio.

- Leave it running and use boto3 with the same credentials & endpoint url.

- `docker compose down` when you're done

- Bind-mount a local directory to the Minio container's `/data/` location to pre-seed
  objects (directories are buckets).

- You can also visit `http://localhost:9001` to see the Minio web console and browse
  around.
