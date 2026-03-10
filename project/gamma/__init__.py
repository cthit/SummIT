"""
Gamma API client for interacting with the Gamma service.

Inspired by [chalmers.it](https://github.com/cthit/chalmers.it) and its typescript client, but implemented in Python.
"""

from .service import GammaService, gamma_url
from .types import (
    GammaGroup,
    GammaGroupMember,
    GammaGroupPost,
    GammaSuperGroup,
    GammaSuperGroupEntry,
    GammaUser,
    GammaUserInfo,
)

__all__ = [
    "GammaService",
    "gamma_url",
    "GammaGroup",
    "GammaGroupMember",
    "GammaGroupPost",
    "GammaSuperGroup",
    "GammaSuperGroupEntry",
    "GammaUser",
    "GammaUserInfo",
]
