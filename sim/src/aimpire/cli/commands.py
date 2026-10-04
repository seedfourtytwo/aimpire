"""The ``qualify`` and ``batch`` subcommands: arguments in, exit code out.

Errors a user can fix (a missing file, a bad profile or experiment, a missing
key) print one line and return 2; a budget refusal returns 3 after the
worst-case line. Nothing else is caught, so a bug still shows its traceback.
"""

import argparse
from typing import Final

from aimpire.cognition.minds import MindError
from aimpire.cognition.profiles import MissingCredential, ProfileError
from aimpire.experiments.batch import ExperimentChanged, run_batch, verify_batch
from aimpire.experiments.experiment import ExperimentError
from aimpire.experiments.preflight import OverBudget
from aimpire.experiments.qualify import run_qualify
from aimpire.experiments.qualify_data import DEFAULT_CASES, DEFAULT_THRESHOLDS

OK: Final = 0
FAILED: Final = 1
BAD_INPUT: Final = 2
OVER_BUDGET: Final = 3
USER_ERRORS: Final = (
    FileNotFoundError,
    FileExistsError,
    MindError,
    ProfileError,
    MissingCredential,
    ExperimentError,
    ExperimentChanged,
)


def qualify_command(args: argparse.Namespace) -> int:
    """``aimpire qualify``: 0 if every mark passed, 1 if not."""
    try:
        result = run_qualify(
            args.mind,
            runs_root=args.runs,
            cases_path=args.cases or DEFAULT_CASES,
            thresholds_path=args.thresholds or DEFAULT_THRESHOLDS,
        )
    except OverBudget as refused:
        print(refused)
        return OVER_BUDGET
    except USER_ERRORS as error:
        print(f"error: {error}")
        return BAD_INPUT
    return OK if result.passed else FAILED


def batch_command(args: argparse.Namespace) -> int:
    """``aimpire batch``: run the experiment, or with ``--verify`` only check its file."""
    try:
        if args.verify:
            changed = verify_batch(args.experiment, out_root=args.out)
            for run_id in changed:
                print(f"edited after run: {run_id}")
            if changed:
                print(f"{len(changed)} runs were made from another version of the file")
                return FAILED
            print("the experiment file matches every recorded run")
            return OK
        run_batch(args.experiment, out_root=args.out)
    except OverBudget as refused:
        print(refused)
        return OVER_BUDGET
    except USER_ERRORS as error:
        print(f"error: {error}")
        return BAD_INPUT
    return OK
