# Cross-MCP Bridge

Other MCP webapps (Plex, Calibre, etc.) can link directly to TVTropes pages via deep-links or the title resolution API.

## Deep-link URL

Constructed by any app that knows the namespace and page name:

```
http://127.0.0.1:10965/?lookup=Film/TheMatrix
http://127.0.0.1:10965/?lookup=Anime/NeonGenesisEvangelion
http://127.0.0.1:10965/?lookup=Literature/HarryPotter
```

The frontend intercepts `?lookup=`, redirects to `/search?trope=...`, and auto-loads that page.

## Title Resolution

For apps that have a title but not the exact page path:

```
GET http://127.0.0.1:10964/api/lookup/title?title=Matrix&hint=movie
→ {"found":true, "namespace":"Film", "page_name":"TheMatrix", ...}
```

The `hint` parameter narrows the search: `movie`, `show`, `anime`, `book`, `game`, `comic`.

## Fleet Bridge Metadata

```json
GET http://127.0.0.1:10964/api/bridge
→ {
    "deep_link_format": "http://127.0.0.1:10965/?lookup={namespace}/{page_name}",
    "api_lookup": "http://127.0.0.1:10964/api/lookup/title?title={title}&hint={hint}",
    "link_templates": {
      "plex_movie": "/?lookup=Film/{title}",
      "plex_show": "/?lookup=Series/{title}",
      "plex_anime": "/?lookup=Anime/{title}",
      "calibre_book": "/?lookup=Literature/{title}"
    },
    "supported_hints": {
      "movie": "Film/ namespace",
      "show": "Series/ namespace",
      "anime": "Anime/ namespace",
      "book": "Literature/ namespace",
      "game": "VideoGame/ namespace"
    }
  }
```

## Template Construction

The simplest integration for other MCP webapps: construct the URL directly.

For a Plex movie titled "The Matrix":
```
http://127.0.0.1:10965/?lookup=Film/TheMatrix
```

For a Calibre book titled "Harry Potter":
```
http://127.0.0.1:10965/?lookup=Literature/HarryPotter
```

The app normalises the title (removes spaces, special chars) and picks the right namespace based on content type.
