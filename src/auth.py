import json
import os
import subprocess
import tempfile

def gcp_connect(secret_name: str = "personal_gcp_key") -> None:
    """
    Authenticate gcloud in Google Colab using a service account JSON stored
    in Colab 'Secrets' (google.colab.userdata).

    Parameters
    ----------
    secret_name:
        Name of the Colab secret that contains the service account JSON text.
    """
    try:
        from google.colab import userdata  # type: ignore
    except Exception as e:
        raise RuntimeError(
            "google.colab is not available. This function must be run inside Google Colab."
        ) from e

    gcp_key = userdata.get(secret_name)
    if not gcp_key or not isinstance(gcp_key, str):
        raise ValueError(
            f"Colab secret '{secret_name}' is missing or empty. "
            "Store the *service account JSON content* in Colab Secrets."
        )

    # Optional validation: ensure it looks like JSON
    try:
        json.loads(gcp_key)
    except Exception as e:
        raise ValueError(
            f"Secret '{secret_name}' does not contain valid JSON."
        ) from e

    fd = None
    key_path = None
    try:
        fd, key_path = tempfile.mkstemp(prefix="gcp-sa-", suffix=".json")
        os.chmod(key_path, 0o600)  # readable/writable only by the current user
        with os.fdopen(fd, "w") as f:
            f.write(gcp_key)

        subprocess.run(
            ["gcloud", "auth", "activate-service-account", "--key-file", key_path],
            check=True,
        )
    finally:
        # Ensure cleanup even if gcloud fails
        if key_path and os.path.exists(key_path):
            try:
                os.remove(key_path)
            except OSError:
                pass
