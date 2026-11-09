from dataclasses import dataclass
from typing import Tuple

gamma_dataclass = dataclass(frozen=True, slots=True)


@gamma_dataclass
class GammaUser:
    """User object returned from Gamma."""

    id: str
    nick: str
    first_name: str
    last_name: str
    acceptance_year: int


@gamma_dataclass
class GammaSuperGroup:
    """A Gamma super group."""

    id: str
    name: str
    pretty_name: str
    type: str
    sv_description: str
    en_description: str


@gamma_dataclass
class GammaPost:
    """Data for which post a user has in a Gamma group."""

    id: str
    sv_name: str
    en_name: str
    email_prefix: str


@gamma_dataclass
class GammaGroupMember:
    """A member of a Gamma group."""

    user: GammaUser
    post: GammaPost
    unofficial_post_name: str | None = None


@gamma_dataclass
class GammaGroup:
    """A sub-group of a Gamma super group."""

    id: str
    name: str
    pretty_name: str
    super_group: GammaSuperGroup
    group_members: Tuple[GammaGroupMember, ...] | None = None


@gamma_dataclass
class GammaGroupPost:
    """A group paired with a post."""

    group: GammaGroup
    post: GammaPost


@gamma_dataclass
class GammaUserInfo:
    """User information returned from ``/api/info/v1/users/<uuid>`` endpoint."""

    user: GammaUser
    groups: Tuple[GammaGroupPost, ...]


@gamma_dataclass
class GammaSuperGroupEntry:
    """An entry in a super group list item."""

    super_group: GammaSuperGroup
    members: Tuple[GammaGroupMember, ...]
    has_banner: bool
    has_avatar: bool


@gamma_dataclass
class GammaSuperGroupListItem:
    """Super group item format returned from ``/info/v1/blob`` endpoint."""

    type: str
    super_groups: Tuple[GammaSuperGroupEntry, ...]


# Super group list returned from ``/info/v1/blob`` endpoint.
GammaSuperGroupBlob = Tuple[GammaSuperGroupListItem, ...]


@gamma_dataclass
class GammaProfile:
    """Profile from OpenID Connect UserInfo endpoint on Gamma."""

    sub: str
    picture: str
    name: str
    cid: str
    given_name: str
    family_name: str
    nickname: str
    locale: str
    email: str | None = None
