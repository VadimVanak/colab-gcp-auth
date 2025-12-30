# colab-gcp-auth

Authenticate **Google Cloud (gcloud)** inside **Google Colab** using a **service account JSON stored in Colab Secrets**.

This avoids committing credentials to notebooks or repositories.

---

## Installation

Install directly in Colab:

```bash
!pip install git+https://github.com/VadimVanak/colab-gcp-auth.git
````

---

## Setup (one-time)

1. Create a **Google Cloud service account**
2. Download the **JSON key**
3. In Colab, open **🔑 Secrets** and add:

   * **Name:** `personal_gcp_key`
   * **Value:** *entire contents of the JSON file*

---

## Usage

```python
from colab_gcp_auth import gcp_connect

gcp_connect()
```

After this, `gcloud` and most Google Cloud SDKs will be authenticated.

Example:

```python
!gcloud projects list
```

### `get_secret_via_gcloud`

Fetches a secret value from **Google Cloud Secret Manager** by invoking the `gcloud` CLI.

The function:
1. Sets the active Google Cloud project.
2. Retrieves the specified secret version.
3. Returns the secret payload as a string.

**Parameters**
- `project_id` (`str`): Google Cloud project ID.
- `secret_id` (`str`): Name of the secret.
- `version` (`str`, optional): Secret version to access (default: `"latest"`).

**Returns**
- `str`: The decoded secret value.

---

## Notes

* Works **only inside Google Colab**
* Authenticates the **gcloud CLI**
* Credentials are written to a temporary file and removed immediately
