#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import datetime
import logging
import json
import math
from dateutil import parser

# Required grants:
#
# user-library-read
# playlist-modify-public
token = "TOKEN_PLACEHOLDER"
group_tracks_by = "year" # month | quarter | year
dry_run = False # setting this to True prevents the script from changing things on your account

def process_status_code(r):
    if r.status_code == 401:
        logging.fatal("Unauthorized. Get a token from https://developer.spotify.com/console/")
        exit(1)
    if math.floor(r.status_code / 10) != 20 :
        logging.fatal("Unexpected request status")
        logging.fatal(r.json())
        exit(1)

def get_json(url):
    """Get JSON resource"""
    headers={"Authorization": "Bearer " + token}
    r = requests.get(url=url, headers=headers)
    process_status_code(r)
    return r.json()

def post(**kwargs):
    """Do a POST request if dry_run == False, otherwise print things"""
    args = ', '.join(['{}={!r}'.format(k, v) for k, v in kwargs.items()])
    logging.debug("POST %s" % args)
    if not dry_run:
        headers={"Authorization": "Bearer " + token}
        r = requests.post(headers=headers, **kwargs)
        process_status_code(r)
        return r.json()
    return dict()


def get_all_pages(url, results=list()):
    """Return all items of a paginated resource"""
    logging.debug("fetching %s" % url)
    res = get_json(url)

    # Recurse if there are further pages
    url_next = res.get("next")
    if url_next != None:
        results = results + get_all_pages(url_next, results=results)
    else:
        logging.debug("no pages left after %s" % url)

    results = results + res.get("items", [])
    logging.info("[%s/%s] %s" % (len(results), res.get("total", "unknown-total-results"), url))
    logging.info("returning %d results" % len(results))
    return results

def get_library_tracks():
    """Return all the tracks saved by the user"""
    logging.info("fetching tracks saved to library")
    url = "https://api.spotify.com/v1/me/tracks"
    return get_all_pages(url)

def get_user_playlists():
    """Return all of the user's playlists"""
    logging.info("fetching user playlists")
    url = "https://api.spotify.com/v1/me/playlists"
    return get_all_pages(url)

def get_user_id():
    """Return the user ID"""
    logging.info("finding out your user id")
    url = "https://api.spotify.com/v1/me"
    uid = get_json(url)["id"]
    logging.info("user id is %s" % uid)
    return uid


def create_playlist(user_id, playlist_name):
    """Create a playlist"""
    logging.info("creating playlist %s" % playlist_name)
    data = {"name": playlist_name, "public": True}
    url = "https://api.spotify.com/v1/users/%s/playlists" % user_id
    res = post(url=url, data=json.dumps(data))
    return res.get("id", "unknown-playlist-id")
    
def add_tracks_to_playlist(track_uris, playlist_name, playlist_id):
    """
    Add tracks to a playlist.
    The tracks are identified by a comma-separated string of track URIs.
    A maximum of 100 tracks is permitted to be added at a time.
    """
    logging.info("adding %s tracks to playlist %s" % (len(track_uris), playlist_name))
    remaining_track_uris = list()
    if len(track_uris) >= 100:
        track_uris = track_uris[:100]
        remaining_track_uris = track_uris[100:]

    data = {"uris": track_uris}
    url = "https://api.spotify.com/v1/playlists/%s/tracks" % playlist_id
    post(url=url, data=json.dumps(data))

    if len(remaining_track_uris) > 0:
        add_tracks_to_playlist(remaining_track_uris, playlist_name, playlist_id)

def map_add_time_to_playlist(added_at):
    """Return the playlist a track belongs to given the time it was added at"""
    year = str(added_at.year)
    year_subgroup = ""

    if group_tracks_by == "month":
        year_subgroup = " " + added_at.month
    elif group_tracks_by == "quarter":
        get_q = lambda m: "Q1" if m < 5 else "Q3" if m > 8 else "Q2"
        year_subgroup = " " + get_q(added_at.month)
    
    logging.info("track created at %s belongs to playlist %s" % (added_at, year + year_subgroup))
    return year +  year_subgroup

def generate_playlists():
    """Build list of playlists and associated tracks"""
    logging.info("generating playlists")
    tracks = get_library_tracks()
    logging.info("found %d tracks" % len(tracks))
    playlists = dict()

    for track in tracks:
        added_at = parser.parse(track["added_at"])
        playlist_name = map_add_time_to_playlist(added_at)
        playlists.setdefault(playlist_name,[]).append(track)

    return playlists

def playlists_filter_existing(playlists):
    """Remove already existing playlists and tracks"""
    playlists_to_create = list()
    playlist_tracks_to_add = dict()
    playlist_id_map = dict()
    user_playlists = get_user_playlists()
    user_playlists_by_name = dict()
    for p in user_playlists:
        user_playlists_by_name[p["name"]] = p
    user_playlist_names = user_playlists_by_name.keys()

    for p in list(playlists.keys()):
        if p not in user_playlist_names:
            logging.debug("playlist %s will be created" % p)
            playlists_to_create.append(p)
            playlist_tracks_to_add[p] = playlists[p]

        else:
            playlist_id_map[p] = user_playlists_by_name[p].get("id", "unknown-playlist-id")
            logging.debug("playlist %s will be updated" % p)
            playlist_tracks_uri = user_playlists_by_name[p]["tracks"]["href"]
            user_playlist_tracks = get_all_pages(playlist_tracks_uri)
            
            user_playlist_track_uris = [t["track"]["uri"] for t in user_playlist_tracks]
            
            for t in playlists[p]:
                if t["track"]["uri"] not in user_playlist_track_uris:
                    playlist_tracks_to_add.setdefault(p,[]).append(t)

    return playlists_to_create, playlist_tracks_to_add, playlist_id_map

def create_playlists_from_library():
    """Create playlists containing user-saved tracks separated by save time"""
    playlists = generate_playlists()
    playlist_names, playlist_tracks, playlist_ids = playlists_filter_existing(playlists)

    if len(playlist_names) > 0:
        logging.info("%d playlists will be created: %s" % (len(playlist_names), ', '.join(playlist_names)))
        user_id = get_user_id()
        for playlist_name in playlist_names:
            playlist_id = create_playlist(user_id, playlist_name)
            playlist_ids[playlist_name] = playlist_id
    else:
        logging.info("no playlist needs to be created")

    playlist_names_to_update = playlist_tracks.keys()
    if len(playlist_names_to_update) > 0:
        logging.info("%d playlists will be created: %s" % (len(playlist_names_to_update), ', '.join(playlist_names_to_update)))
        for playlist_name in playlist_names_to_update:
            track_uris = [t["track"]["uri"] for t in playlists[playlist_name]]
            track_uris.reverse()
            add_tracks_to_playlist(track_uris, playlist_name, playlist_ids[playlist_name])
    else:
        logging.info("no playlist has to be updated")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    create_playlists_from_library()
    
