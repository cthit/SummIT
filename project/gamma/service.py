import os
from urllib3 import HTTPSConnectionPool
from urllib.parse import urlparse
import json
from .types import (
    GammaGroup,
    GammaSuperGroup,
    GammaUserInfo,
    GammaSuperGroupEntry,
)
from .parse import (
    parse_client_group,
    parse_user_info,
    parse_supergroup_list_item,
)


def gamma_url() -> str:
    return os.getenv("GAMMA_ROOT_URL", "https://auth.chalmers.it").rstrip("/")


def gamma_host() -> str:
    parsed = urlparse(gamma_url())
    if parsed.netloc:
        return parsed.netloc
    return gamma_url().replace("https://", "").replace("http://", "").rstrip("/")


def _gamma_auth_header() -> str:
    return os.getenv("AUTH_HEADER", "")


class GammaService:
    _active_group_types = os.getenv("ACTIVE_GROUP_TYPES", "committee").split(",")
    _https = HTTPSConnectionPool(
        host=gamma_host(),
        assert_hostname=gamma_host(),
        headers={"Authorization": _gamma_auth_header()},
    )

    @staticmethod
    def _gamma_get_request(endpoint: str) -> dict:
        response = GammaService._https.request(
            "GET",
            "/api" + endpoint,
        )

        if response.status != 200:
            body = None
            try:
                body = json.loads(response.data or b"")
            except Exception:
                body = response.data
            raise Exception(f"Gamma request failed with status {response.status}", body)

        return json.loads(response.data or b"{}")

    @staticmethod
    def get_gamma_user(user_uuid: str) -> GammaUserInfo:
        raw = GammaService._gamma_get_request(f"/info/v1/users/{user_uuid}")
        return parse_user_info(raw)

    @staticmethod
    def get_nick(user_uuid: str) -> str | None:
        try:
            return GammaService.get_gamma_user(user_uuid).user.nick
        except Exception:
            return None

    @staticmethod
    def get_user_avatar_url(user_uuid: str) -> str:
        return f"{gamma_url()}/images/user/avatar/{user_uuid}"

    @staticmethod
    def get_group_avatar_url(group_id: str) -> str:
        return f"{gamma_url()}/images/group/avatar/{group_id}"

    @staticmethod
    def get_super_group_avatar_url(super_group_id: str) -> str:
        return f"{gamma_url()}/images/super-group/avatar/{super_group_id}"

    @staticmethod
    def get_super_group_banner_url(super_group_id: str) -> str:
        return f"{gamma_url()}/images/super-group/banner/{super_group_id}"

    @staticmethod
    def get_group_banner_url(group_id: str) -> str:
        return f"{gamma_url()}/images/group/banner/{group_id}"

    @staticmethod
    def is_super_group_active(sg: GammaSuperGroup) -> bool:
        return sg.type in GammaService._active_group_types

    @staticmethod
    def is_group_active(g: GammaGroup) -> bool:
        return GammaService.is_super_group_active(g.super_group)

    @staticmethod
    def get_all_super_groups() -> tuple[GammaSuperGroupEntry, ...]:
        data = GammaService._gamma_get_request("/info/v1/blob")
        entries: list[GammaSuperGroupEntry] = []
        for item in data:
            entries.extend(parse_supergroup_list_item(item).super_groups)
        return tuple(entries)

    @staticmethod
    def get_super_group(super_group_id: str) -> GammaSuperGroup | None:
        for entry in GammaService.get_all_super_groups():
            if entry.super_group.id == super_group_id:
                return entry.super_group
        return None

    @staticmethod
    def get_all_active_groups() -> list[dict[str, str]]:
        data = GammaService._gamma_get_request("/client/v1/groups")
        groups: list[dict[str, str]] = []

        for group in data:
            try:
                parsed = parse_client_group(group)
            except Exception:
                continue
            if not GammaService.is_group_active(parsed):
                continue
            groups.append({"id": parsed.id, "name": parsed.pretty_name})

        groups.sort(key=lambda g: g["name"].lower())
        return groups
