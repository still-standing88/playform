from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum, auto
from typing import List, Dict, Optional, Union, Type, Any, Callable, Iterable
from pathlib import Path

import os
import json
import re
import urllib.parse
import urllib.request


class PlaylistFormat(Enum):
    M3U = auto()
    M3U8 = auto()
    XSPF = auto()
    PLS = auto()
    JSON = auto()
    UNKNOWN = auto()


@dataclass
class PlaylistEntry:
    location: str
    title: Optional[str] = None
    duration: Optional[int] = None
    artist: Optional[str] = None
    album: Optional[str] = None
    metadata: Dict[str, Any]|None = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class PlaylistParser(ABC):
    @classmethod
    @abstractmethod
    def parse(cls, content: str) -> List[PlaylistEntry]:
        pass
    
    @classmethod
    @abstractmethod
    def serialize(cls, entries: List[PlaylistEntry], original_content: Optional[str] = None) -> str:
        pass
    
    @staticmethod
    def normalize_path(path: str) -> str:
        if re.match(r'^https?://', path):
            return path
        
        return os.path.normpath(path)
    
    @staticmethod
    def is_url(path: str) -> bool:
        return bool(re.match(r'^https?://', path))


class M3UParser(PlaylistParser):
    @classmethod
    def parse(cls, content: str) -> List[PlaylistEntry]:
        entries = []
        lines = content.splitlines()
        i = 0
        
        while i < len(lines):
            line = lines[i].strip()
            
            if not line or line.startswith('#') and not line.startswith('#EXTINF:'):
                i += 1
                continue
            
            title = None
            duration = None
            
            if line.startswith('#EXTINF:'):
                extinf_parts = line[8:].split(',', 1)
                try:
                    duration = int(float(extinf_parts[0]))
                except ValueError:
                    duration = None
                
                if len(extinf_parts) > 1:
                    title = extinf_parts[1].strip()
                
                i += 1
                if i >= len(lines):
                    break
                    
                line = lines[i].strip()
            
            if line and not line.startswith('#'):
                location = cls.normalize_path(line)
                entries.append(PlaylistEntry(location=location, title=title, duration=duration))
            
            i += 1
        
        return entries
    
    @classmethod
    def serialize(cls, entries: List[PlaylistEntry], original_content: Optional[str] = None) -> str:
        header = "#EXTM3U\n" if not original_content or original_content.strip().startswith("#EXTM3U") else ""
        lines = [header] if header else []
        
        for entry in entries:
            if entry.title or entry.duration is not None:
                duration_str = str(entry.duration) if entry.duration is not None else "-1"
                title = entry.title or ""
                lines.append(f"#EXTINF:{duration_str},{title}")
            
            lines.append(entry.location)
        
        return "\n".join(lines)


class M3U8Parser(M3UParser):
    @classmethod
    def serialize(cls, entries: List[PlaylistEntry], original_content: Optional[str] = None) -> str:
        content = super().serialize(entries, original_content)
        return content


class PLSParser(PlaylistParser):
    @classmethod
    def parse(cls, content: str) -> List[PlaylistEntry]:
        entries = []
        lines = content.splitlines()
        
        file_map = {}
        title_map = {}
        length_map = {}
        
        num_entries = 0
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            if line.lower().startswith('[playlist]'):
                continue
                
            if '=' not in line:
                continue
                
            key, value = line.split('=', 1)
            key = key.strip().lower()
            value = value.strip()
            
            if key.startswith('file'):
                try:
                    index = int(key[4:])
                    file_map[index] = cls.normalize_path(value)
                    num_entries = max(num_entries, index)
                except ValueError:
                    pass
                    
            elif key.startswith('title'):
                try:
                    index = int(key[5:])
                    title_map[index] = value
                except ValueError:
                    pass
                    
            elif key.startswith('length'):
                try:
                    index = int(key[6:])
                    try:
                        length_map[index] = int(float(value)) if value != '-1' else None
                    except ValueError:
                        length_map[index] = None
                except ValueError:
                    pass
        
        for i in range(1, num_entries + 1):
            if i in file_map:
                title = title_map.get(i)
                duration = length_map.get(i)
                entries.append(PlaylistEntry(location=file_map[i], title=title, duration=duration))
        
        return entries
    
    @classmethod
    def serialize(cls, entries: List[PlaylistEntry], original_content: Optional[str] = None) -> str:
        lines = ["[playlist]"]
        lines.append(f"NumberOfEntries={len(entries)}")
        
        for i, entry in enumerate(entries, 1):
            lines.append(f"File{i}={entry.location}")
            
            if entry.title:
                lines.append(f"Title{i}={entry.title}")
            else:
                lines.append(f"Title{i}=")
                
            duration = -1 if entry.duration is None else entry.duration
            lines.append(f"Length{i}={duration}")
        
        lines.append("Version=2")
        return "\n".join(lines)


class XSPFParser(PlaylistParser):
    @classmethod
    def parse(cls, content: str) -> List[PlaylistEntry]:
        try:
            import xml.etree.ElementTree as ET
            entries = []
            
            root = ET.fromstring(content)
            ns = {'ns': 'http://xspf.org/ns/0/'}
            
            for track in root.findall('.//ns:track', ns):
                location_elem = track.find('ns:location', ns)
                title_elem = track.find('ns:title', ns)
                creator_elem = track.find('ns:creator', ns)
                album_elem = track.find('ns:album', ns)
                duration_elem = track.find('ns:duration', ns)
                
                location = cls.normalize_path(location_elem.text.strip()) if location_elem is not None and location_elem.text else ""
                title = title_elem.text if title_elem is not None and title_elem.text else None
                artist = creator_elem.text if creator_elem is not None and creator_elem.text else None
                album = album_elem.text if album_elem is not None and album_elem.text else None
                
                duration = None
                if duration_elem is not None and duration_elem.text:
                    try:
                        duration = int(int(duration_elem.text) / 1000)  # Convert from milliseconds to seconds
                    except ValueError:
                        duration = None
                
                if location:
                    entries.append(PlaylistEntry(
                        location=location,
                        title=title,
                        artist=artist,
                        album=album,
                        duration=duration
                    ))
            
            return entries
        except Exception:
            return []
    
    @classmethod
    def serialize(cls, entries: List[PlaylistEntry], original_content: Optional[str] = None) -> str:
        try:
            import xml.etree.ElementTree as ET
            import xml.dom.minidom as minidom
            
            ET.register_namespace('', 'http://xspf.org/ns/0/')
            
            root = None
            if original_content:
                try:
                    root = ET.fromstring(original_content)
                except:
                    root = None
            
            if root is None:
                root = ET.Element('{http://xspf.org/ns/0/}playlist')
                ET.SubElement(root, '{http://xspf.org/ns/0/}title').text = "Playlist"
                ET.SubElement(root, '{http://xspf.org/ns/0/}creator').text = "Media Library"
                ET.SubElement(root, '{http://xspf.org/ns/0/}info')
                
            tracklist = root.find('.//{http://xspf.org/ns/0/}trackList')
            if tracklist is None:
                tracklist = ET.SubElement(root, '{http://xspf.org/ns/0/}trackList')
            else:
                for child in list(tracklist):
                    tracklist.remove(child)
            
            for entry in entries:
                track = ET.SubElement(tracklist, '{http://xspf.org/ns/0/}track')
                
                location = ET.SubElement(track, '{http://xspf.org/ns/0/}location')
                location.text = entry.location
                
                if entry.title:
                    title = ET.SubElement(track, '{http://xspf.org/ns/0/}title')
                    title.text = entry.title
                
                if entry.artist:
                    creator = ET.SubElement(track, '{http://xspf.org/ns/0/}creator')
                    creator.text = entry.artist
                
                if entry.album:
                    album = ET.SubElement(track, '{http://xspf.org/ns/0/}album')
                    album.text = entry.album
                
                if entry.duration is not None:
                    duration = ET.SubElement(track, '{http://xspf.org/ns/0/}duration')
                    duration.text = str(entry.duration * 1000)  # Convert to milliseconds
            
            xml_str = ET.tostring(root, encoding='unicode')
            dom = minidom.parseString(xml_str)
            formatted_xml = dom.toprettyxml(indent='  ')
            
            return formatted_xml
        except Exception as e:
            return f"<?xml version='1.0' encoding='UTF-8'?>\n<playlist xmlns='http://xspf.org/ns/0/'>\n  <title>Playlist</title>\n  <trackList>\n  </trackList>\n</playlist>"


class JSONParser(PlaylistParser):
    @classmethod
    def parse(cls, content: str) -> List[PlaylistEntry]:
        try:
            data = json.loads(content)
            entries = []
            
            if isinstance(data, dict) and "tracks" in data and isinstance(data["tracks"], list):
                for track in data["tracks"]:
                    if isinstance(track, dict) and "location" in track:
                        entry = PlaylistEntry(
                            location=cls.normalize_path(track["location"]),
                            title=track.get("title"),
                            artist=track.get("artist"),
                            album=track.get("album"),
                            duration=track.get("duration"),
                            metadata={k: v for k, v in track.items() if k not in ["location", "title", "artist", "album", "duration"]}
                        )
                        entries.append(entry)
            elif isinstance(data, list):
                for track in data:
                    if isinstance(track, dict) and "location" in track:
                        entry = PlaylistEntry(
                            location=cls.normalize_path(track["location"]),
                            title=track.get("title"),
                            artist=track.get("artist"),
                            album=track.get("album"),
                            duration=track.get("duration"),
                            metadata={k: v for k, v in track.items() if k not in ["location", "title", "artist", "album", "duration"]}
                        )
                        entries.append(entry)
            
            return entries
        except:
            return []
    
    @classmethod
    def serialize(cls, entries: List[PlaylistEntry], original_content: Optional[str] = None) -> str:
        structure_type = "object"  # Default
        
        if original_content:
            try:
                data = json.loads(original_content)
                if isinstance(data, list):
                    structure_type = "array"
            except:
                pass
        
        if structure_type == "array":
            tracks = []
            for entry in entries:
                track = {
                    "location": entry.location
                }
                
                if entry.title:
                    track["title"] = entry.title
                
                if entry.artist:
                    track["artist"] = entry.artist
                
                if entry.album:
                    track["album"] = entry.album
                
                if entry.duration is not None:
                    track["duration"] = entry.duration
                
                if entry.metadata:
                    track.update(entry.metadata)
                
                tracks.append(track)
            
            return json.dumps(tracks, indent=2)
        else:
            playlist = {"tracks": []}
            
            for entry in entries:
                track = {
                    "location": entry.location
                }
                
                if entry.title:
                    track["title"] = entry.title
                
                if entry.artist:
                    track["artist"] = entry.artist
                
                if entry.album:
                    track["album"] = entry.album
                
                if entry.duration is not None:
                    track["duration"] = entry.duration
                
                if entry.metadata:
                    track.update(entry.metadata)
                
                playlist["tracks"].append(track)
            
            return json.dumps(playlist, indent=2)


class Playlist:
    def __init__(self, title: Optional[str] = None):
        self.title = title or "New Playlist"
        self.entries: List[PlaylistEntry] = []
        self._original_content: Optional[str] = None
        self._format: Optional[PlaylistFormat] = None
        self._parsers: Dict[PlaylistFormat, Type[PlaylistParser]] = {
            PlaylistFormat.M3U: M3UParser,
            PlaylistFormat.M3U8: M3U8Parser,
            PlaylistFormat.XSPF: XSPFParser,
            PlaylistFormat.PLS: PLSParser,
            PlaylistFormat.JSON: JSONParser
        }
        self._custom_parsers: Dict[str, Type[PlaylistParser]] = {}
    
    def register_parser(self, format_type: Union[PlaylistFormat, str], parser_class: Type[PlaylistParser]) -> None:
        if isinstance(format_type, PlaylistFormat):
            self._parsers[format_type] = parser_class
        else:
            self._custom_parsers[format_type] = parser_class
    
    def _detect_format(self, file_path: Union[str, Path]) -> PlaylistFormat:
        file_path = str(file_path)
        file_path_lower = file_path.lower()
        
        if file_path_lower.endswith('.m3u8'):
            return PlaylistFormat.M3U8
        elif file_path_lower.endswith('.m3u'):
            return PlaylistFormat.M3U
        elif file_path_lower.endswith('.xspf'):
            return PlaylistFormat.XSPF
        elif file_path_lower.endswith('.pls'):
            return PlaylistFormat.PLS
        elif file_path_lower.endswith('.json'):
            return PlaylistFormat.JSON
        else:
            return PlaylistFormat.UNKNOWN
    
    def load(self, file_path_or_url: Union[str, Path], format_type: Optional[PlaylistFormat] = None, encoding: str = 'utf-8') -> 'Playlist':
        file_path_str = str(file_path_or_url)
        
        if not format_type:
            format_type = self._detect_format(file_path_str)
            
            if format_type == PlaylistFormat.UNKNOWN:
                raise ValueError(f"Cannot determine playlist format for file: {file_path_str}")
        
        self._format = format_type
        
        if re.match(r'^https?://', file_path_str):
            with urllib.request.urlopen(file_path_str) as response:
                content = response.read().decode(encoding)
        else:
            with open(file_path_str, 'r', encoding=encoding) as f:
                content = f.read()
        
        self._original_content = content
        
        parser_class = self._parsers.get(format_type)
        if not parser_class:
            raise ValueError(f"No parser registered for format: {format_type}")
        
        self.entries = parser_class.parse(content)
        return self
    
    def save(self, file_path: Union[str, Path], format_type: Optional[PlaylistFormat] = None, encoding: str = 'utf-8') -> None:
        file_path_str = str(file_path)
        
        if not format_type:
            if self._format:
                format_type = self._format
            else:
                format_type = self._detect_format(file_path_str)
                
                if format_type == PlaylistFormat.UNKNOWN:
                    raise ValueError(f"Cannot determine playlist format for file: {file_path_str}")
        
        parser_class = self._parsers.get(format_type)
        if not parser_class:
            raise ValueError(f"No parser registered for format: {format_type}")
        
        content = parser_class.serialize(self.entries, self._original_content if format_type == self._format else None)
        
        with open(file_path_str, 'w', encoding=encoding) as f:
            f.write(content)
    
    def add_entry(self, entry: PlaylistEntry) -> None:
        self.entries.append(entry)
    
    def remove_entry(self, index: int) -> Optional[PlaylistEntry]:
        if 0 <= index < len(self.entries):
            return self.entries.pop(index)
        return None
    
    def move_entry(self, from_index: int, to_index: int) -> bool:
        if 0 <= from_index < len(self.entries) and 0 <= to_index < len(self.entries):
            entry = self.entries.pop(from_index)
            self.entries.insert(to_index, entry)
            return True
        return False
    
    def clear(self) -> None:
        self.entries.clear()
    
    def get_entry(self, index: int) -> Optional[PlaylistEntry]:
        if 0 <= index < len(self.entries):
            return self.entries[index]
        return None
    
    def jump_to_track(self, index: int) -> Optional[PlaylistEntry]:
        if 0 <= index < len(self.entries):
            return self.entries[index]
        return None
    
    def sort(self, key: Union[str, Callable[[PlaylistEntry], Any]], reverse: bool = False) -> None:
        if isinstance(key, str):
            attr = key
            key = lambda entry: getattr(entry, attr) if getattr(entry, attr) is not None else ""
        
        self.entries.sort(key=key, reverse=reverse)
    
    def filter(self, predicate: Callable[[PlaylistEntry], bool]) -> 'Playlist':
        result = Playlist(self.title)
        result.entries = [entry for entry in self.entries if predicate(entry)]
        result._format = self._format
        result._original_content = self._original_content
        return result
    
    def remove_duplicates(self, key: Union[str, Callable[[PlaylistEntry], Any]] = "location") -> int:
        if isinstance(key, str):
            attr = key
            key = lambda entry: getattr(entry, attr)
        
        seen = set()
        unique_entries = []
        removed_count = 0
        
        for entry in self.entries:
            entry_key = key(entry)
            if entry_key not in seen:
                seen.add(entry_key)
                unique_entries.append(entry)
            else:
                removed_count += 1
        
        self.entries = unique_entries
        return removed_count
    
    def filter_by_extension(self, allowed_extensions: List[str], include: bool = True) -> int:
        allowed_extensions = [ext.lower() for ext in allowed_extensions]
        filtered_count = 0
        
        def has_allowed_extension(entry: PlaylistEntry) -> bool:
            location = entry.location.lower()
            file_ext = os.path.splitext(location)[1][1:] if os.path.splitext(location)[1] else ""
            return (file_ext in allowed_extensions) == include
        
        original_count = len(self.entries)
        self.entries = [entry for entry in self.entries if has_allowed_extension(entry)]
        filtered_count = original_count - len(self.entries)
        
        return filtered_count
    
    def merge(self, other: 'Playlist') -> 'Playlist':
        merged = Playlist(f"{self.title} + {other.title}")
        merged.entries = self.entries.copy()
        merged.entries.extend(other.entries)
        return merged
    
    def __len__(self) -> int:
        return len(self.entries)
    
    def __getitem__(self, index: int) -> PlaylistEntry:
        return self.entries[index]
    
    def __iter__(self):
        return iter(self.entries)


class PlaylistManager:
    def __init__(self):
        self.playlists: Dict[str, Playlist] = {}
    
    def create_playlist(self, name: str, title: Optional[str] = None) -> Playlist:
        playlist = Playlist(title)
        self.playlists[name] = playlist
        return playlist
    
    def get_playlist(self, name: str) -> Optional[Playlist]:
        return self.playlists.get(name)
    
    def remove_playlist(self, name: str) -> bool:
        if name in self.playlists:
            del self.playlists[name]
            return True
        return False
    
    def load_playlist(self, name: str, file_path_or_url: Union[str, Path], 
                     format_type: Optional[PlaylistFormat] = None,
                     encoding: str = 'utf-8') -> Playlist:
        playlist = Playlist()
        playlist.load(file_path_or_url, format_type, encoding)
        self.playlists[name] = playlist
        return playlist
    
    def save_playlist(self, name: str, file_path: Union[str, Path], 
                     format_type: Optional[PlaylistFormat] = None,
                     encoding: str = 'utf-8') -> bool:
        playlist = self.get_playlist(name)
        if playlist:
            playlist.save(file_path, format_type, encoding)
            return True
        return False
    
    def list_playlists(self) -> List[str]:
        return list(self.playlists.keys())
    
    def merge_playlists(self, name: str, source_playlist_names: List[str], 
                       title: Optional[str] = None) -> Optional[Playlist]:
        if not source_playlist_names:
            return None
        
        source_playlists = [self.get_playlist(name) for name in source_playlist_names]
        
        if any(playlist is None for playlist in source_playlists):
            return None
        
        merged_playlist = source_playlists[0]
        for playlist in source_playlists[1:]:
            merged_playlist = merged_playlist.merge(playlist)
        
        if title:
            merged_playlist.title = title
            
        self.playlists[name] = merged_playlist
        return merged_playlist
    
    def sort_playlist(self, name: str, key: Union[str, Callable[[PlaylistEntry], Any]], 
                     reverse: bool = False) -> bool:
        playlist = self.get_playlist(name)
        if playlist:
            playlist.sort(key=key, reverse=reverse)
            return True
        return False
    
    def filter_playlist(self, source_name: str, target_name: str, 
                       predicate: Callable[[PlaylistEntry], bool],
                       title: Optional[str] = None) -> Optional[Playlist]:
        source_playlist = self.get_playlist(source_name)
        if not source_playlist:
            return None
        
        filtered_playlist = source_playlist.filter(predicate)
        if title:
            filtered_playlist.title = title
            
        self.playlists[target_name] = filtered_playlist
        return filtered_playlist
    
    def remove_duplicates(self, name: str, key: Union[str, Callable[[PlaylistEntry], Any]] = "location") -> int:
        playlist = self.get_playlist(name)
        if playlist:
            return playlist.remove_duplicates(key)
        return 0
    
    def filter_by_extension(self, name: str, allowed_extensions: List[str], include: bool = True) -> int:
        playlist = self.get_playlist(name)
        if playlist:
            return playlist.filter_by_extension(allowed_extensions, include)
        return 0
