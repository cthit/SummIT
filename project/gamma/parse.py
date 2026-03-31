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
    return GammaUser(
        id=data["id"],
        nick=data["nick"],
        first_name=data["firstName"],
        last_name=data["lastName"],
        acceptance_year=data["acceptanceYear"],
    )


def parse_post(data: dict) -> GammaPost:
    return GammaPost(
        id=data["id"],
        sv_name=data["svName"],
        en_name=data["enName"],
        email_prefix=data.get("emailPrefix", ""),
    )


def parse_group_member(data: dict) -> GammaGroupMember:
    return GammaGroupMember(
        user=parse_user(data["user"]),
        post=parse_post(data["post"]),
        unofficial_post_name=data.get("unofficialPostName"),
    )


def parse_super_group(data: dict) -> GammaSuperGroup:
    return GammaSuperGroup(
        id=data["id"],
        name=data["name"],
        pretty_name=data["prettyName"],
        type=data["type"],
        sv_description=data["svDescription"],
        en_description=data["enDescription"],
    )


def parse_group(data: dict) -> GammaGroup:
    members = data.get("groupMembers")
    return GammaGroup(
        id=data["id"],
        name=data["name"],
        pretty_name=data["prettyName"],
        super_group=parse_super_group(data["superGroup"]),
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
        super_group=parse_super_group(data["superGroup"]),
        members=tuple(parse_group_member(m) for m in data.get("members", [])),
        has_banner=data.get("hasBanner", False),
        has_avatar=data.get("hasAvatar", False),
    )


def parse_supergroup_list_item(data: dict) -> GammaSuperGroupListItem:
    return GammaSuperGroupListItem(
        type=data["type"],
        super_groups=tuple(
            parse_supergroup_entry(e) for e in data.get("superGroups", [])
        ),
    )
