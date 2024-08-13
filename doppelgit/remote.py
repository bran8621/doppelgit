import os
import logging
from typing import Dict, Set, Optional

from . import base, data

# Constants
REMOTE_REFS_BASE = "refs/heads/"
LOCAL_REFS_BASE = "refs/remote/"

# Logger setup
logger = logging.getLogger(__name__)


def fetch(remote_path: str) -> None:
    """
    Fetches missing objects and updates local references to match the server.

    Args:
        remote_path: Path to the remote repository.
    """
    try:
        logger.info(f"Fetching objects from remote repository at '{remote_path}'...")

        refs = _get_remote_refs(remote_path, REMOTE_REFS_BASE)

        for oid in base.iter_objects_in_commits(refs.values()):
            data.fetch_object_if_missing(oid, remote_path)

        for remote_name, value in refs.items():
            refname = os.path.relpath(remote_name, REMOTE_REFS_BASE)
            local_ref_path = os.path.join(LOCAL_REFS_BASE, refname)
            data.update_ref(local_ref_path, data.RefValue(symbolic=False, value=value))

        logger.info("Fetch operation completed successfully.")

    except Exception as e:
        logger.error(f"Fetch operation failed: {e}")
        raise


def push(remote_path: str, refname: str) -> None:
    """
    Pushes local changes to the remote repository.

    Args:
        remote_path: Path to the remote repository.
        refname: Name of the reference to push.
    """
    try:
        logger.info(f"Pushing local changes to remote repository at '{remote_path}'...")

        remote_refs = _get_remote_refs(remote_path)
        remote_ref = remote_refs.get(refname)
        local_ref = data.get_ref(refname).value

        if not local_ref:
            raise ValueError(f"Local ref '{refname}' does not exist.")

        if remote_ref and not base.is_ancestor_of(local_ref, remote_ref):
            raise ValueError(
                f"Force push detected: '{local_ref}' is not an ancestor of '{remote_ref}'."
            )

        known_remote_refs = filter(data.object_exists, remote_refs.values())
        remote_objects = set(base.iter_objects_in_commits(known_remote_refs))
        local_objects = set(base.iter_objects_in_commits({local_ref}))
        objects_to_push = local_objects - remote_objects

        for oid in objects_to_push:
            data.push_object(oid, remote_path)

        with data.change_git_dir(remote_path):
            data.update_ref(refname, data.RefValue(symbolic=False, value=local_ref))

        logger.info("Push operation completed successfully.")

    except Exception as e:
        logger.error(f"Push operation failed: {e}")
        raise


def _get_remote_refs(remote_path: str, prefix: str = "") -> Dict[str, Optional[str]]:
    """
    Retrieves remote references from the remote repository.

    Args:
        remote_path: Path to the remote repository.
        prefix: Prefix for filtering remote references.

    Returns:
        dict: A dictionary of remote references.
    """
    try:
        with data.change_git_dir(remote_path):
            return {refname: ref.value for refname, ref in data.iter_refs(prefix)}
    except Exception as e:
        raise RuntimeError(f"Failed to retrieve remote refs from '{remote_path}': {e}")
