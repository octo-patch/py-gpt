#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# ================================================== #

import sys
import typing


_PYGPT_SELF_TYPE = typing.TypeVar("_PyGPTSelf")


def ensure_typing_self_compat() -> None:
    """
    Make ``Self`` safe in runtime typing expressions on Python < 3.11.

    Python 3.10 has no native PEP 673 ``typing.Self``. Some dependency
    combinations used by local Whisper/PyTorch may nevertheless expose an
    object as ``typing.Self`` that is a plain ``typing._SpecialForm``. Python
    3.10 then rejects it when a library evaluates e.g. ``Optional[Self]`` or
    ``Union[..., Self]`` and raises::

        TypeError: Plain typing.Self is not valid as type argument

    A TypeVar is sufficient for runtime evaluation and mirrors the underlying
    semantics of ``Self`` closely enough for imports/type-hint evaluation. The
    shim is installed before importing local Whisper and is a no-op on Python
    3.11+, where ``typing.Self`` is native.
    """
    if sys.version_info >= (3, 11):
        return

    # Install first, before importing typing_extensions. On Python 3.10 this
    # also prevents packages from creating/injecting an incompatible
    # typing.Self during their import sequence.
    typing.Self = _PYGPT_SELF_TYPE

    try:
        import typing_extensions
    except ImportError:
        return

    ext_self = getattr(typing_extensions, "Self", None)
    if ext_self is None:
        typing_extensions.Self = _PYGPT_SELF_TYPE
        return

    # Modern typing_extensions.Self is compatible with Python 3.10. Keep it
    # when possible; replace only a broken/old implementation.
    try:
        typing.Optional[ext_self]
    except TypeError:
        typing_extensions.Self = _PYGPT_SELF_TYPE
