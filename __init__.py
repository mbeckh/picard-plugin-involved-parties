# Copyright 2026 Michael Beckh (mbeckh)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Load MusicBrainz id and legal names for composers, lyricists, producers and writers."""

from __future__ import annotations

from collections import OrderedDict
from functools import partial
import itertools
import threading
from typing import TYPE_CHECKING, cast

from picard import mbjson
from picard.const import ALIAS_TYPE_LEGAL_NAME_ID


if TYPE_CHECKING:
    from collections.abc import Callable

    from PyQt6 import QtNetwork

    from picard.plugin3.api import (
        Album,
        Metadata,
        PluginApi,
        Track,
    )
    from picard.webservice import PendingRequest


_CACHE_MAX_ENTRIES = 1000


class _CacheEntry:
    legal: str
    waiting: list[Callable[[str], None]]
    request: PendingRequest

    def __init__(self, callback: Callable[[str], None]) -> None:
        self.waiting = [callback]

    def is_loaded(self) -> bool:
        return hasattr(self, 'legal')

    def is_aborted(self) -> bool:
        return hasattr(self, 'request') and self.request.aborted

    def set_loaded(self, legal: str) -> None:
        self.legal = legal
        for callback in self.waiting:
            callback(legal)
        del self.waiting
        del self.request


_lock = threading.Lock()
_cache = OrderedDict[str, _CacheEntry]()


def _received_artist_data(
    artist: dict,
    _reply,
    error: QtNetwork.QNetworkReply.NetworkError | Exception | None,
    *,
    api: PluginApi,
    album: Album | None,
    task_id: str,
    artist_id: str,
) -> None:
    try:
        if error:
            api.logger.error("Error loading involved party '%s': %s", artist_id, error)
            with _lock:
                del _cache[artist_id]
            return

        legal = ''
        for alias in (a for a in artist.get('aliases', ()) if a['type-id'] == ALIAS_TYPE_LEGAL_NAME_ID):
            if legal:
                api.logger.warning("Legal name not unique for '%s': '%s' vs. '%s'", artist_id, legal, alias)
            legal = alias['name']
        if not legal:
            legal = artist['name']
        legal = legal.strip()

        with _lock:
            _cache[artist_id].set_loaded(legal)
            _cache.move_to_end(artist_id)
    finally:
        if album:
            api.complete_album_task(album, task_id)


def _load_details(api: PluginApi, album: Album | None, artist_id: str, cache_entry: _CacheEntry) -> None:
    task_id = f'InvolvedParty={artist_id}'

    def request() -> PendingRequest:
        cache_entry.request = api.mb_api._get_by_id(
            entitytype='artist',
            entityid=artist_id,
            handler=partial(_received_artist_data, api=api, album=album, task_id=task_id, artist_id=artist_id),
            inc=['aliases'],
        )
        return cache_entry.request

    if album:
        api.add_album_task(
            album=album,
            task_id=task_id,
            description=f"Get info for artist: {artist_id}",
            request_factory=request,
            blocking=True,
        )
    else:
        request()

    with _lock:
        # remove oldest loaded entries until target size reached
        for key in itertools.islice(
            (k for k, v in _cache.items() if v.is_loaded() or v.is_aborted()), max(len(_cache) - _CACHE_MAX_ENTRIES, 0)
        ):
            del _cache[key]


def _get_details(api: PluginApi, album: Album | None, artist_id: str, callback: Callable[[str], None]) -> None:
    with _lock:
        entry = _cache.get(artist_id)
        if entry:
            if entry.is_loaded():
                callback(entry.legal)
                _cache.move_to_end(artist_id)
            else:
                entry.waiting.append(callback)
            return

        entry = _CacheEntry(callback)
        _cache[artist_id] = entry

    _load_details(api, album, artist_id, entry)


def _replace_mbid_with_name(metadata: Metadata, key: str, artist_id: str, name: str) -> None:
    values = metadata.getall(key)
    values = [name if item == artist_id else item for item in values]
    metadata.set(key, values)


def _add_artist_data(api: PluginApi, album: Album | None, metadata: Metadata, node: dict[str, dict]) -> None:
    for relation in (rel for rel in node.get('relations', ()) if rel and rel.get('target-type') == 'artist'):
        reltype = mbjson._ARTIST_REL_TYPES.get(cast('str', relation['type']))
        artist = relation.get('artist')
        if not reltype or not artist:
            return
        artist_id = artist['id']
        if reltype not in {'composer', 'lyricist', 'producer', 'writer'}:
            continue

        key = f'~aipd_{reltype}_id'
        if artist_id in metadata.getall(key):
            continue

        metadata.add(key, artist_id)

        key = f'~aipd_{reltype}_legal'
        metadata.add(key, artist_id)  # use mbid and switch to name later (keeps order)

        _get_details(api, album, artist_id, partial(_replace_mbid_with_name, metadata, key, artist_id))


def _add_additional_party_ids(
    api: PluginApi,
    track: Track,
    metadata: Metadata,
    track_node: dict[str, dict],
    _release_node: dict | None = None,
) -> None:
    album = track.album
    if recording := track_node.get('recording'):
        _add_artist_data(api, album, metadata, recording)
        for work in (
            rel['work']
            for rel in recording.get('relations', ())
            if rel['type'] == 'performance' and rel['target-type'] == 'work'
        ):
            _add_artist_data(api, album, metadata, work)


def enable(api: PluginApi) -> None:
    """Register the track metadata processor."""
    api.register_track_metadata_processor(_add_additional_party_ids)


def disable() -> None:
    """Currently a no-op."""
