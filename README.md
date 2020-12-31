# Unofficial MangaUpdates API

A simple python package for accessing data from MangaUpdates, acting as an 
*unofficial* API. (In Progress...)

## Usage

If you want to get info on One Piece (`id = 33`)

```python3
>>> from mangaupdates import public
>>> manga = public.Manga(33)
>>> manga.populate()          # execute GET request
>>> manga.title
'One Piece'
>>> manga.series_type
'Manga'
>>> manga.related_series
[(164909, 'Chin Piece', '(Spin-Off)'), (60414, 'Chopperman', '(Spin-Off)'), ...
>>> manga.associated_names
['Budak Getah (Malay)', 'قطعة واحدة', 'وان پیس', 'ون بيس', 'วันพีซ', ...
>>> manga.groups_scanlating
[(5816, '/a/nonymous'), (2931, 'A-Team'), (2595, 'Akatsuki'), ...
```
