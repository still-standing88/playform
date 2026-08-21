def MediaInfo(*args, **kwargs):
    import music_tag
    return music_tag.load_file(*args, **kwargs)
