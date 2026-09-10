#    MTUOC-segmenter
#    Copyright (C) 2023  Antoni Oliver
#    Copyright (C) 2026  Gonzalo López-Sánchez
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <https://www.gnu.org/licenses/>.

from typing import (List, Set, Tuple, Dict, Optional)
from ..utils.get_language import get_language
from pathlib import Path
import sys
from tqdm import tqdm

class SrxSegmenter:
    """
    Handle segmentation with SRX regex format.
    """
    def __init__(self, rule: Dict[str, List[Tuple[str, Optional[str]]]], source_text: str) -> None:
        self.source_text = source_text
        self.non_breaks = rule.get('non_breaks', [])
        self.breaks = rule.get('breaks', [])

    def _get_break_points(self, regexes: List[Tuple[str, str]]) -> Set[int]:
        import regex
        return set([
            match.span(1)[1]
            for before, after in regexes
            for match in regex.finditer('({})({})'.format(before, after), self.source_text)
        ])

    def get_non_break_points(self) -> Set[int]:
        """
        Return segment non break points
        """
        return self._get_break_points(self.non_breaks)

    def get_break_points(self) -> Set[int]:
        """
        Return segment break points
        """
        return self._get_break_points(self.breaks)

    def extract(self) -> Tuple[List[str], List[str]]:
        """
        Return segments and whitespaces.
        """
        non_break_points = self.get_non_break_points()
        candidate_break_points = self.get_break_points()

        break_point = sorted(candidate_break_points - non_break_points)
        source_text = self.source_text

        segments = []  # type: List[str]
        whitespaces = []  # type: List[str]
        previous_foot = ""
        for start, end in zip([0] + break_point, break_point + [len(source_text)]):
            segment_with_space = source_text[start:end]
            candidate_segment = segment_with_space.strip()
            if not candidate_segment:
                previous_foot += segment_with_space
                continue

            head, segment, foot = segment_with_space.partition(candidate_segment)

            segments.append(segment)
            whitespaces.append('{}{}'.format(previous_foot, head))
            previous_foot = foot
        whitespaces.append(previous_foot)

        return segments, whitespaces

def parse(srx_filepath: str) -> Dict[str, Dict[str, List[Tuple[str, Optional[str]]]]]:
    """
    Parse SRX file and return it.
    :param srx_filepath: is source SRX file.
    :return: dict
    """
    import lxml.etree

    tree = lxml.etree.parse(srx_filepath)
    namespaces = {
        'ns': 'http://www.lisa.org/srx20'
    }

    rules = {}

    for languagerule in tree.xpath('//ns:languagerule', namespaces=namespaces):
        rule_name = languagerule.attrib.get('languagerulename')
        if rule_name is None:
            continue

        current_rule = {
            'breaks': [],
            'non_breaks': [],
        }

        for rule in languagerule.xpath('ns:rule', namespaces=namespaces):
            is_break = rule.attrib.get('break', 'yes') == 'yes'
            rule_holder = current_rule['breaks'] if is_break else current_rule['non_breaks']

            beforebreak = rule.find('ns:beforebreak', namespaces=namespaces)
            beforebreak_text = '' if beforebreak.text is None else beforebreak.text

            afterbreak = rule.find('ns:afterbreak', namespaces=namespaces)
            afterbreak_text = '' if afterbreak.text is None else afterbreak.text

            rule_holder.append((beforebreak_text, afterbreak_text))

        rules[rule_name] = current_rule

    return rules

def segmenta(cadena, srxfile, srxlang):
    srxfile=srxfile
    srxlang = srxlang
    rules = parse(srxfile)
    
    segmenter = SrxSegmenter(rules[srxlang],cadena)
    segments=segmenter.extract()
    resposta=[]
    for segment in segments[0]:
        segment=segment.replace("’","'")
        resposta.append(segment)
    resposta="\n".join(resposta)
    return(resposta)

def detect_encoding(file_path):
    from charset_normalizer import from_path

    result = from_path(file_path).best()
    return result.encoding if result else 'utf-8'

def sort_uniq_shuf(segments_folder, lang_code, outdir):
    import subprocess
    print("Deduplicating segments")

    cmd = f'find {segments_folder} -type f -print0 | xargs -0 cat | sort | uniq | shuf > {outdir}/unique-segments-{lang_code.lower()}.txt'

    subprocess.run(
        cmd,
        shell=True,
        check=True
    )
    print(f"Unique segments file saved in {outdir}")

def load_external_segmenter(lang_name, lang_code, external_segmenter="stanza"): 
    # implement spacy in the future?
    # if external_segmenter.lower() == 'stanza':
    import stanza
    print(f"Running Stanza segmenter in {lang_name}")
    return stanza.Pipeline(lang=lang_code, processors='tokenize', use_gpu=False)
    
    # elif external_segmenter.lower() == 'spacy':
    #     import spacy
    #     print(f"Running spaCy segmenter in {lang_name}")
    #     return spacy.load(lang_code)

def external_segmenter(nlp, text, external_segmenter):
    if external_segmenter.lower() == 'stanza':
        doc = nlp(text)
        return [sentence.text for sentence in doc.sentences]
    
    # elif external_segmenter.lower() == 'spacy':
    #     doc = nlp(text)
    #     return [sent.text for sent in doc.sents]
    
def pack_jsonl(input_file, output_file):
    import json
    with open(input_file, "r") as fl, open(output_file, "w", encoding="utf-8") as out:
        for line in fl:
            path = line.strip()

            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    text = f.read()

                obj = {
                    "text": text,
                    "source": Path(path).name
                }

                out.write(json.dumps(obj) + "\n")

            except Exception:
                continue

def chunk_corpus(pages_folder, chunks_folder):
    import subprocess
    import glob
    import math

    with open(f"{chunks_folder}/file_names/all_file_names.txt", "w") as outfile:
        subprocess.run(
            ["find", f"{pages_folder}/", "-type", "f", "-name", "*.txt"],
            stdout=outfile,
            check=True)

        print("File names compiled")

    with open(f"{chunks_folder}/file_names/all_file_names.txt", "r") as f:
        num_files = sum(1 for file_name in f)

    chunk_size = math.ceil(num_files / 100) # to compile and chunk the corpus into 100 files

    print(f"Chunking corpus into 100 files. Each file contains {chunk_size} articles")
    subprocess.run(
    ["split", "-l", f"{chunk_size}", f"{chunks_folder}/file_names/all_file_names.txt", f"{chunks_folder}/file_names/files_chunk_"],
    check=True)
    print("File names chunked")

    print("\nProcessing chunks")
    for f in tqdm(glob.glob(f"{chunks_folder}/file_names/files_chunk_*")):
        file_ending = f.split("_")
        file_ending = file_ending[-1]

        # print(f"Processing {f}")

        pack_jsonl(f, f"{chunks_folder}/chunk_{file_ending}.jsonl")

def segment_corpus(args):
    import sys
    from pathlib import Path
    import json
    print("\nRunning segment command")

    # accessing args
    tool_folder = Path(__file__).parent.parent.parent

    if args.srxfile:
        srxfile = args.srxfile
    else:
        srxfile = tool_folder / "segment.srx"
        print(f"SRX file found")

    rules = parse(srxfile)
    languages = list(rules.keys())
    force_srx_lang = args.force_srx_lang
    force_segmenter = args.force_segmenter
    chunk = args.chunk

    indir = args.indir # should be the pages folder
    indir = Path(indir)

    outdir = args.outdir or indir.parent

    if indir.is_dir():

        print(f"Folder {indir.name} found")
        ending = indir.name.split("-") # splitting folder name to get the language code
        ending = ending[-1]
        srxlang_name, srxlang_code = get_language(ending)

        if force_srx_lang:
            print(f"Overriding SRX language configuration.")
            srxlang_name = force_srx_lang.lower()
            print(f"{force_srx_lang.capitalize()} chosen")
                
        if not force_srx_lang and not force_segmenter: # if we want to use the srx file
            srxlang_name, srxlang_code = get_language(ending)
            if not srxlang_name in languages:
                print("Language ",srxlang_name," not available in ", srxfile)
                print("Available languages:",", ".join(languages))
                sys.exit()

        if force_segmenter: # basically if else, using stanza
            force_segmenter_name = "stanza"
            srxlang_name, srxlang_code = get_language(ending)
            nlp = load_external_segmenter(srxlang_name, srxlang_code, force_segmenter_name.lower())

        print(f"Segmenting files in {srxlang_name.capitalize()}")

        if not force_srx_lang:
            segments_folder = indir.parent / f'segments-{srxlang_code}'
            segments_folder.mkdir(parents=True, exist_ok=True)
            print(f"{segments_folder} created")

        else:
            segments_folder = indir.parent / f'segments-force-{srxlang_name}-{ending}'
            segments_folder.mkdir(parents=True, exist_ok=True)
            print(f"{segments_folder} created")

        # txt files
        if not chunk:
            for text_file in indir.rglob("*.txt"): # accessing all txt files
                encoding = detect_encoding(text_file)
                # reading the file
                with open(text_file, "r", encoding=encoding, errors="ignore") as entrada:
                    
                    outfile = segments_folder / text_file.name
                    # writing segments in a new file of segmented sentences
                    with open(outfile, "w", encoding="utf-8") as sortida:
                        # process file here
                        for linia in entrada:
                            if force_segmenter:
                                segments = external_segmenter(nlp, linia, force_segmenter_name.lower())
                            else:
                                segments = segmenta(linia, srxfile, srxlang_name.capitalize())

                            if len(segments) > 0:
                                # if paramark:
                                #     sortida.write("<p>\n")

                                if not force_segmenter:
                                    sortida.write(segments + "\n")
                                else:
                                    sortida.write("\n".join(segments) + "\n")

        # jsonl files test
        if chunk:
            print("\nChunking corpus")
            chunks_folder = indir.parent / f"chunks-{srxlang_code}"
            file_names_folder = chunks_folder / "file_names"

            if not chunks_folder.exists():
                chunks_folder.mkdir(parents=True, exist_ok=True)
                print(f"{chunks_folder} created")
                file_names_folder.mkdir(parents=True, exist_ok=True)

            chunk_corpus(pages_folder=indir, chunks_folder=chunks_folder)
            print("\nSegmenting chunks")
            for jsonl_file in tqdm(chunks_folder.rglob("*.jsonl")):
                # reading the file
                with open(jsonl_file, "r", encoding='utf-8') as entrada:
                    
                    outfile = segments_folder / f"seg_{jsonl_file.stem}.txt"
                
                    with open(outfile, "w", encoding="utf-8") as sortida:
                        # process file here
                        for linia in entrada:

                            try:
                                doc = json.loads(linia)
                                text = doc["text"]
                            except Exception:
                                continue

                            if force_segmenter:
                                segments = external_segmenter(nlp, text, force_segmenter_name.lower())
                            else:
                                segments = segmenta(text, srxfile, srxlang_name.capitalize())

                            if isinstance(segments, str):
                                segments = segments.splitlines()

                            for segment in segments:
                                if not force_segmenter:
                                    sortida.write(segment + "\n")
                                else:
                                    sortida.write("\n".join(segments) + "\n")

        if not force_srx_lang:
            sort_uniq_shuf(segments_folder, srxlang_code, outdir)

        else:
            srxlang_code = f'force-{srxlang_name}-{ending}'
            sort_uniq_shuf(segments_folder, srxlang_code, outdir)

        print(f"Segmenting finished")