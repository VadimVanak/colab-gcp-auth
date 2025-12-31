# colab-gcp-auth

A tiny helper package to make **Google Colab notebooks** work seamlessly with **Google Cloud Run Jobs** (after `nbconvert`) **without code changes**.

It provides:

1. **GCP authentication** in Colab using a **service account JSON stored in Colab Secrets**
2. **Data transfer** between local paths and **GCS buckets** via `gsutil` (`cp` / `rsync`)
3. **Secret access** via the **google-cloud-secret-manager** Python client (ADC)
4. **CLI-arg simulation** in Colab via `get_argv()` for `argparse`-based notebooks/scripts

---

## Installation (in Colab)

```bash
!pip install git+https://github.com/VadimVanak/colab-gcp-auth.git
````

---

## One-time setup (Colab Secrets)

1. Create a **Google Cloud service account**
2. Grant it the roles you need (e.g. Storage + Secret Manager access)
3. Download the **JSON key**
4. In Colab, open **🔑 Secrets** and add:

* **Name:** `personal_gcp_key`
* **Value:** *(paste the entire JSON key contents)*

> ⚠️ Keep this key private. Anyone with it can act as the service account.

---

## Quick start

```python
from colab_gcp_auth import gcp_connect, gcp_get_secret, gcp_transfer

# Authenticate both gcloud/gsutil and Python client libraries (ADC)
gcp_connect(project_id="your-project-id")

# Read a secret via the Secret Manager Python client
token = gcp_get_secret("your-project-id", "MY_SECRET")
print(token)

# Sync a local folder to a GCS prefix
gcp_transfer("./data", "gs://my-bucket/data", mode="rsync")
```

After `gcp_connect()`, CLI tools work too:

```python
!gcloud projects list
!gsutil ls gs://my-bucket
```

---

## API

### `gcp_connect(project_id=None, colab_secret_name="personal_gcp_key") -> str`

Authenticates in **Google Colab** using a service account JSON stored in Colab Secrets and configures:

* **gcloud / gsutil** via `gcloud auth activate-service-account`
* **Python Google Cloud client libraries** via ADC (`GOOGLE_APPLICATION_CREDENTIALS`)

**Parameters**

* `project_id` (`str | None`): If set, runs `gcloud config set project <project_id>`.
* `colab_secret_name` (`str`): Colab secret name containing the JSON text.

**Returns**

* `str`: Path to the temporary service account key file.

**Notes**

* The key file is written to a temporary path and kept for the notebook session so ADC continues working.
* You can delete it manually when done, but then Python ADC-based clients will stop working.

---

### `gcp_get_secret(project_id, secret_id, version_id="latest") -> str`

Fetches a secret value from **Google Cloud Secret Manager** using the
`google-cloud-secret-manager` Python library.

**Parameters**

* `project_id` (`str`): GCP project ID.
* `secret_id` (`str`): Secret name.
* `version_id` (`str`): Secret version (default: `"latest"`).

**Returns**

* `str`: Secret payload decoded as UTF-8.

**Requires**

* `pip install google-cloud-secret-manager` (usually pulled in via your environment/package deps)

---

### `gcp_transfer(src, dst, mode="rsync", delete=False, checksum=False, preserve_posix=False, dry_run=False, extra_args=None) -> None`

A convenience wrapper around `gsutil` for transferring between local paths and `gs://...`.

**Supports**

* `mode="rsync"` (default): directory-oriented syncing
* `mode="cp"`: file or directory copy

**Highlights**

* Uses `gsutil -m` for parallelism (multi-thread/process).
* If a directory is involved, it uses recursive behavior (`rsync -r` / `cp -r`).
* If `mode="rsync"` but `src` is a local file, it falls back to `cp`.

**Common options**

* `delete=True` (rsync): delete destination files not present in source (`-d`)
* `checksum=True` (rsync): compare checksums (`-c`)
* `preserve_posix=True` (cp): preserve POSIX attributes where supported (`-p`)
* `dry_run=True`: print the command without running it
* `extra_args=[...]`: append advanced `gsutil` flags

---

### `get_argv(PARAMS="") -> list[str]`

Makes notebooks compatible with `argparse` both in Colab and when run as a script after `nbconvert`.

* In **Colab**:

  * if `PARAMS` is non-empty, it is parsed like a CLI string and returned as `argv`
* Outside Colab:

  * returns `sys.argv` unchanged

Example:

```python
import argparse
from colab_gcp_auth import get_argv

parser = argparse.ArgumentParser()
parser.add_argument("--input", required=True)

args = parser.parse_args(get_argv('--input gs://my-bucket/data'))
print(args.input)
```

---

## Typical workflow: Colab → Cloud Run Job (nbconvert)

1. Develop in Colab with:

   * `gcp_connect()` for auth
   * `gcp_transfer()` to pull/push data
   * `gcp_get_secret()` for secrets
   * `get_argv()` to simulate CLI args

2. Convert with `nbconvert` and run the same code as a Cloud Run Job script,
   passing real CLI args normally.

---

## Notes / troubleshooting

* This package is intended primarily for **Google Colab**.
* Your service account must have the right IAM permissions, for example:

  * Storage: `roles/storage.objectViewer` / `roles/storage.objectAdmin`
  * Secret Manager: `roles/secretmanager.secretAccessor`
* If Secret Manager access works via `gcloud` but not Python, it usually means
  ADC is not set up — `gcp_connect()` sets `GOOGLE_APPLICATION_CREDENTIALS` for you.
