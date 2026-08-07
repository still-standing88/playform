import pysubs2
import os
import re
import charset_normalizer

def detect_encoding(file_path):
    try:
        results = charset_normalizer.from_path(file_path)
        best_match = results.best()
        if best_match:
            return best_match.encoding
        return 'utf-8'
    except Exception:
        return 'utf-8'

def read_subtitle_file(file_path, encoding='utf-8'):
    try:
        subs = pysubs2.load(file_path, encoding=encoding)
        events = []
        for i, line in enumerate(subs):
            events.append({
                "index": str(i + 1),
                "start": pysubs2.time.ms_to_str(line.start, fractions=True),
                "end": pysubs2.time.ms_to_str(line.end, fractions=True),
                "text": line.plaintext
            })
        return events
    except Exception as e:
        return f"Error reading file with '{encoding}' encoding: {str(e)}"

def parse_time(time_str):
    if not time_str:
        return 0
    parts = re.findall(r'(-?\d+\.?\d*)([hms])', time_str)
    ms = 0
    for val, unit in parts:
        val = float(val)
        if unit == 'h':
            ms += 3600000 * val
        elif unit == 'm':
            ms += 60000 * val
        elif unit == 's':
            ms += 1000 * val
    return int(ms)

def convert_and_clean_subtitles(files, output_dir, options):
    try:
        for file_path in files:
            subs = pysubs2.load(file_path, encoding=options["input_encoding"])
            
            if options["clean_subtitles"]:
                subs.remove_miscellaneous_events()

            base_name = os.path.basename(file_path)
            name_without_ext = os.path.splitext(base_name)[0]
            output_filename = f"{name_without_ext}.{options['output_format']}"
            output_path = os.path.join(output_dir, output_filename)

            save_options = {
                "encoding": options["output_encoding"],
                "format_": options["output_format"],
                "keep_unknown_html_tags": options["srt_keep_unknown_html_tags"],
                "keep_html_tags": options["srt_keep_html_tags"],
                "keep_ssa_tags": options["srt_keep_ssa_tags"],
                "write_fps_declaration": not options["sub_no_write_fps_declaration"]
            }
            
            subs.save(output_path, **save_options)
        return f"Success: Processed {len(files)} file(s)."
    except Exception as e:
        return f"Error: {str(e)}"

def process_subtitles(files, output_dir, options):
    try:
        for file_path in files:
            subs = pysubs2.load(file_path, encoding=options["input_encoding"])

            shift_ms = parse_time(options["shift_time"])
            if shift_ms != 0:
                subs.shift(ms=shift_ms)

            if options["transform_framerate"]:
                subs.transform_framerate(
                    in_fps=options["from_fps"],
                    out_fps=options["to_fps"]
                )

            if options["text_operation"] != "None":
                for line in subs:
                    original_text = line.plaintext
                    modified_text = original_text
                    op = options["text_operation"]

                    if op == "Find and Replace":
                        find_text = options["find_text"]
                        replace_text = options["replace_text"]
                        if find_text:
                            if options["case_sensitive"]:
                                modified_text = original_text.replace(find_text, replace_text)
                            else:
                                modified_text = re.sub(find_text, replace_text, original_text, flags=re.IGNORECASE)
                    elif op == "Add Prefix/Suffix":
                        modified_text = f"{options['prefix']}{original_text}{options['suffix']}"
                    elif op == "Change Case":
                        style = options["case_style"]
                        if style == "UPPERCASE":
                            modified_text = original_text.upper()
                        elif style == "lowercase":
                            modified_text = original_text.lower()
                        elif style == "Title Case":
                            modified_text = original_text.title()
                    
                    line.plaintext = modified_text

            subs.save(os.path.join(output_dir, os.path.basename(file_path)))
        return f"Success: Processed {len(files)} file(s)."
    except Exception as e:
        return f"Error: {str(e)}"
