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

---

## Notes

* Works **only inside Google Colab**
* Authenticates the **gcloud CLI**
* Credentials are written to a temporary file and removed immediately
