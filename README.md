# Boomerang Classic EPG

This starter repo builds a Central time XMLTV EPG for the Jpuffle5 Boomerang Classic schedule and provides a small one-channel playlist for TiviMate.

## Files

- `playlist.m3u`: One-channel playlist for Boomerang Classic.
- `build_epg.py`: Builds `epg.xml` using the Fandom schedule.
- `.github/workflows/build-epg.yml`: Runs the EPG builder every 6 hours and manually from the Actions tab.

## TiviMate URLs

Replace `YOUR-GITHUB-USERNAME` with your GitHub username.

Playlist:

```txt
https://raw.githubusercontent.com/YOUR-GITHUB-USERNAME/boomerang-classic-epg/main/playlist.m3u
```

EPG:

```txt
https://raw.githubusercontent.com/YOUR-GITHUB-USERNAME/boomerang-classic-epg/main/epg.xml
```

## Matching ID

The playlist and EPG intentionally use this unique ID:

```txt
boomerang-classic-jpuffle5
```

This avoids the `24.7.Dummy.us` ID from the DrewLive playlist, which is reused by many unrelated 24/7 channels.
