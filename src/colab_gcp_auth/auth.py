import json
import os
import sys
import shlex
import subprocess
import tempfile
from typing import Iterable, Optional, List


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


def gcp_get_secret(
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


def get_argv(PARAMS: str = ""):
    """
    Return an argv list suitable for argparse.

    - In Google Colab:
        * If PARAMS is a non-empty CLI-like string, it is parsed and used
        * The program name is taken from sys.argv[0] if available, otherwise 'notebook'
    - Outside Colab (including nbconvert → .py execution):
        * Returns sys.argv unchanged
    """
    # Detect Colab without external helpers
    in_colab = "google.colab" in sys.modules

    # Determine a stable program name for help / usage messages
    prog = (
        os.path.basename(sys.argv[0])
        if sys.argv and sys.argv[0]
        else "notebook"
    )

    if in_colab and PARAMS.strip():
        return [prog] + shlex.split(PARAMS)

    return sys.argv


def gcp_transfer(
    src: str,
    dst: str,
    mode: str = "rsync",
    *,
    delete: bool = False,
    checksum: bool = False,
    preserve_posix: bool = False,
    dry_run: bool = False,
    extra_args: Optional[Iterable[str]] = None,
) -> None:
    """
    Wrapper around `gsutil` for copying / syncing between local paths and GCS.

    Parameters
    ----------
    src, dst:
        Source and destination paths. Either can be a local path or a GCS URL (gs://...).
        For folder transfers, pass a folder path (local dir or gs://bucket/prefix).
    mode:
        "rsync" (default) or "cp".
    delete:
        If True and mode="rsync", pass `-d` to delete extra files at destination.
    checksum:
        If True and mode="rsync", pass `-c` to compare checksums instead of mtime/size.
    preserve_posix:
        If True and mode="cp", pass `-p` (preserve POSIX attributes where supported).
    dry_run:
        If True, print the gsutil command instead of running it.
    extra_args:
        Extra args appended to the gsutil command (advanced use).

    Notes
    -----
    - Uses `gsutil -m` for parallelism (multi-thread/process) automatically.
    - If a local directory is detected (os.path.isdir), copies/syncs recursively.
    - `gsutil rsync` is directory-oriented. If mode="rsync" but src is a local file,
      this function falls back to `cp`.
    """
    mode = (mode or "rsync").strip().lower()
    if mode not in {"rsync", "cp"}:
        raise ValueError(f"mode must be 'rsync' or 'cp', got: {mode}")

    def is_gcs(p: str) -> bool:
        return p.startswith("gs://")

    def local_is_dir(p: str) -> bool:
        return (not is_gcs(p)) and os.path.isdir(p)

    def local_is_file(p: str) -> bool:
        return (not is_gcs(p)) and os.path.isfile(p)

    args: List[str] = ["gsutil", "-m"]

    # Decide whether this is a directory transfer (best-effort)
    dir_like = local_is_dir(src) or local_is_dir(dst)
    # If src is a local file, rsync doesn't make sense -> cp fallback
    if mode == "rsync" and local_is_file(src):
        mode = "cp"

    if mode == "rsync":
        # rsync is for directories/prefixes; -r to include subfolders
        args += ["rsync", "-r"]
        if delete:
            args.append("-d")
        if checksum:
            args.append("-c")
        args += [src, dst]
    else:
        # cp supports files and directories
        args += ["cp"]
        if preserve_posix:
            args.append("-p")
        if dir_like:
            args.append("-r")  # recursive copy of folder + subfolders
        args += [src, dst]

    if extra_args:
        args.extend(list(extra_args))

    if dry_run:
        print(" ".join(args))
        return

    subprocess.run(args, check=True)
