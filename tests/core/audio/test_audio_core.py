#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.02 18:00:00                  #
# ================================================== #

from unittest.mock import MagicMock, patch

from tests.mocks import mock_window
from pygpt_net.core.audio import Audio


def test_clean_text():
    """Test clean text"""
    audio = Audio()
    text = 'speak this<tool>>ignore this</tool> only'
    res = audio.clean_text(text)
    assert res == 'speak this only'



def test_get_memory_excluded_bytes_sums_provider_values():
    """Audio core aggregates memory exclusions reported by providers."""
    audio = Audio()
    provider_a = MagicMock()
    provider_b = MagicMock()
    provider_a.get_memory_excluded_bytes.return_value = 100
    provider_b.get_memory_excluded_bytes.return_value = 250
    audio.providers = {
        "input": {"a": provider_a},
        "output": {"b": provider_b},
    }

    assert audio.get_memory_excluded_bytes() == 350


def test_get_memory_excluded_bytes_ignores_invalid_provider_values():
    """Broken or negative provider accounting must not break renderer cleanup."""
    audio = Audio()
    provider_negative = MagicMock()
    provider_broken = MagicMock()
    provider_negative.get_memory_excluded_bytes.return_value = -500
    provider_broken.get_memory_excluded_bytes.side_effect = RuntimeError("boom")
    audio.providers = {
        "input": {
            "negative": provider_negative,
            "broken": provider_broken,
        },
    }

    assert audio.get_memory_excluded_bytes() == 0
