import json
import os
import subprocess
import tempfile
from typing import Optional


def gcp_connect(
    *,
    project_id: Optional[str] = None,
    colab_secret_name: str = "personal_gcp_key",
) -> str:
    """
    Authenticate in Google Colab using a service account JSON stored in Colab Secrets,
    and configure both:
      - gcloud/gsutil (via `gcloud auth activate-service-account`)
      - Python client libraries (via ADC using GOOGLE_APPLICATION_CREDENTIALS)

    Parameters
    ----------
    project_id:
        If provided, runs `gcloud config set project <project_id>`.
    colab_secret_name:
        Name of the Colab secret that contains the *service account JSON text*.

    Returns
    -------
    key_path:
        Path to the temporary service account key file (kept for the session so ADC works).
        You can delete it manually when you're done, but then Python ADC will stop working.
    """
    try:
        from google.colab import userdata  # type: ignore
    except Exception as e:
        raise RuntimeError("This function must be run inside Google Colab.") from e

    key_json_text = userdata.get(colab_secret_name)
    if not key_json_text or not isinstance(key_json_text, str):
        raise ValueError(
            f"Colab secret '{colab_secret_name}' is missing/empty. "
            "Store the *service account JSON content* in Colab Secrets."
        )

    # Validate JSON early
    try:
        json.loads(key_json_text)
    except Exception as e:
        raise ValueError(f"Secret '{colab_secret_name}' does not contain valid JSON.") from e

    # Write key to a temp file. Keep it for the notebook session so ADC can keep using it.
    fd, key_path = tempfile.mkstemp(prefix="gcp-sa-", suffix=".json")
    os.chmod(key_path, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write(key_json_text)

    # Make Python client libraries pick it up via ADC.
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = key_path

    # Activate for gcloud/gsutil.
    subprocess.run(
        ["gcloud", "auth", "activate-service-account", "--key-file", key_path],
        check=True,
    )

    if project_id:
        subprocess.run(["gcloud", "config", "set", "project", project_id], check=True)

    return key_path


def get_secret_via_gcloud(
    project_id: str,
    secret_id: str,
    version_id: str = "latest",
) -> str:
    """
    Read a secret from Google Secret Manager using google-cloud-secret-manager.

    Assumes you've called `gcp_connect()` first (so ADC credentials exist).
    """
    from google.cloud import secretmanager  # pip: google-cloud-secret-manager

    client = secretmanager.SecretManagerServiceClient()  # uses ADC by default
    name = f"projects/{project_id}/secrets/{secret_id}/versions/{version_id}"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("utf-8")
