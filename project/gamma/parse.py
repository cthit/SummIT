"""Utility routines for converting raw JSON from Gamma into dataclasses.

This keeps the logic decoupled from the transport layer in ``service.py`` and
makes the parsers easier to test in isolation.
"""

from __future__ import annotations

from .types import (
    GammaGroup,
    GammaGroupPost,
    GammaGroupMember,
    GammaPost,
    GammaSuperGroup,
    GammaSuperGroupEntry,
    GammaSuperGroupListItem,
    GammaUser,
    GammaUserInfo,
)


def parse_user(data: dict) -> GammaUser:
    return GammaUser(**data)


def parse_post(data: dict) -> GammaPost:
    return GammaPost(**data)


def parse_group_member(data: dict) -> GammaGroupMember:
    return GammaGroupMember(
        user=parse_user(data["user"]),
        post=parse_post(data["post"]),
        unofficial_post_name=data.get("unofficial_post_name"),
    )


def parse_super_group(data: dict) -> GammaSuperGroup:
    return GammaSuperGroup(**data)


def parse_group(data: dict) -> GammaGroup:
    members = data.get("group_members")
    return GammaGroup(
        id=data["id"],
        name=data["name"],
        pretty_name=data["pretty_name"],
        super_group=parse_super_group(data["super_group"]),
        group_members=(
            tuple(parse_group_member(m) for m in members)
            if members is not None
            else None
        ),
    )


def parse_group_post(data: dict) -> GammaGroupPost:
    return GammaGroupPost(
        group=parse_group(data["group"]),
        post=parse_post(data["post"]),
    )


def parse_user_info(data: dict) -> GammaUserInfo:
    return GammaUserInfo(
        user=parse_user(data["user"]),
        groups=tuple(parse_group_post(g) for g in data.get("groups", [])),
    )


def parse_supergroup_entry(data: dict) -> GammaSuperGroupEntry:
    return GammaSuperGroupEntry(
        super_group=parse_super_group(data["super_group"]),
        members=tuple(parse_group_member(m) for m in data.get("members", [])),
        has_banner=data.get("has_banner", False),
        has_avatar=data.get("has_avatar", False),
    )


def parse_supergroup_list_item(data: dict) -> GammaSuperGroupListItem:
    return GammaSuperGroupListItem(
        type=data["type"],
        super_groups=tuple(
            parse_supergroup_entry(e) for e in data.get("super_groups", [])
        ),
    )
