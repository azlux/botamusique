Current implementation:
```
 +----------------------------------------------------------+
 | BaseItem <-| FileItem <-- URLItem <-- URLFromPlaylistItem|
 |          <-| RadioItem                                   |
 +----------------------------------------------------------+
  ^
  |
  v
  +--------------------+
  |PlayList            |
  |PlaylistItemWrapper |
  +--------------------+
```

Goal:
```
+----------------------------------------------------------+
|          <-| URLItem <-- URLFromPlaylistItem             |
| BaseItem <-| FileItem                                    |
|          <-| RadioItem                                   |
++---------------------------------------------------------+
 ^
 |
 v
 +-----------+
 |PlayList   |
 |           |
 +-----------+

```
