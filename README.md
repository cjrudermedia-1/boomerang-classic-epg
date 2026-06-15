# Boomerang Classic EPG

This starter repo builds a Central time XMLTV EPG for the Jpuffle5 Boomerang Classic schedule and provides a small one-channel playlist for TiviMate.

## GitHub repository

Use this repository name under the GitHub username `cjrudermedia-1`:

```txt
boomerang-classic-epg
```

## Files

- `playlist.m3u`: One-channel playlist for Boomerang Classic using the Rumble stream URL.
- `build_epg.py`: Builds `epg.xml` using the Fandom schedule in `America/Chicago` time.
- `.github/workflows/build-epg.yml`: Runs the EPG builder every 6 hours and manually from the Actions tab.

## TiviMate URLs

Playlist:

```txt
https://raw.githubusercontent.com/cjrudermedia-1/boomerang-classic-epg/main/playlist.m3u
```

EPG:

```txt
https://raw.githubusercontent.com/cjrudermedia-1/boomerang-classic-epg/main/epg.xml
```

## Matching ID

The playlist and EPG intentionally use this unique ID:

```txt
boomerang-classic-jpuffle5
```

This avoids the `24.7.Dummy.us` ID from the DrewLive playlist, which is reused by many unrelated 24/7 channels.

## Channel stream

The playlist points to this stream:

```txt
https://rumble.com/live-hls-dvr/78ivl8/playlist.m3u8?
```

## TiviMate setup

1. Add the playlist URL above as a playlist.
2. Add the EPG URL above as an EPG source.
3. Enable the EPG source for the Boomerang Classic playlist.
4. Refresh the EPG.
5. If needed, manually assign the EPG entry named `Boomerang Classic` to the channel.
