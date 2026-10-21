#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.02 17:45:00                  #
# ================================================== #

# Official model names accepted by the current openai-whisper package.
# Values are user-facing labels. Sizes are approximate checkpoint download
# sizes on disk (not RAM/VRAM usage). Keep this mapping easy to update when
# upstream adds or removes model aliases.
WHISPER_LOCAL_MODELS = {
    "tiny": "tiny (~75 MB)",
    "tiny.en": "tiny.en (~75 MB)",
    "base": "base (~142 MB)",
    "base.en": "base.en (~142 MB)",
    "small": "small (~466 MB)",
    "small.en": "small.en (~466 MB)",
    "medium": "medium (~1.5 GB)",
    "medium.en": "medium.en (~1.5 GB)",
    "large-v1": "large-v1 (~2.9 GB)",
    "large-v2": "large-v2 (~2.9 GB)",
    "large-v3": "large-v3 (~2.9 GB)",
    "large": "large (~2.9 GB)",
    "large-v3-turbo": "large-v3-turbo (~1.6 GB)",
    "turbo": "turbo (~1.6 GB)",
}
