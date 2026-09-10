#!/usr/bin/python3
# Copyright (C) 2021  Antoni Oliver
# Copyright (C) 2026  Gonzalo López Sánchez
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from .commands.create import create_corpora
from .commands.segment import segment_corpus
from .commands.align import align_corpora
from .commands.rescore import rescore_corpus
from .commands.select import select_corpus
from .commands.pipeline import pipeline
from .commands.database import generate_database

import argparse

def cli():          
    parser = argparse.ArgumentParser(
        description=
        '''
        Tool that allows the creation, segmentation, alignment, rescoring and segment selection of parallel corpora from Wikipedia. It supports step-by-step execution and full pipeline execution. That is, commands may be run individually, e.g., in order to inspect results between steps, or execute the entire workflow at once using the 'pipeline' command.
        '''
        )
    subparsers = parser.add_subparsers(required=True)
    
# CREATE SUBPARSER
    create_parser = subparsers.add_parser("create", help="Create a corpus from Wikipedia.", description="Create a corpus or parallel corpora from Wikipedia dumps.")
    create_parser.add_argument('lang1', help='Name or ISO code of the source language.')
    create_parser.add_argument('lang2', help='Name or ISO code of the target language. Keep empty to create a monolingual corpus.', nargs="?", default=None)
    create_parser.add_argument("-c", "--categories", action="store", help='Wikipedia categories to search. Must be in between quotation marks ("") and separated by a comma (,).', required=False)
    create_parser.add_argument("-d", '--depth', type=int, help='Recursion depth for traversing the category tree.', required=False)
    create_parser.add_argument('--restrict', action='store_true', help='Restrict L2 pages to equivalent L1 pages.', required=False)
    create_parser.add_argument('--database', help='The directory where the CCW SQLite database is. Default: database/', required=False)
    create_parser.add_argument('--dumps', help='Wikipedia dumps path. Default: dumps/', required=False)   
    create_parser.add_argument('--outdir', help='Name of the output directory. Default: corpora-lang1-lang2/. Language codes will be added automatically.',required=False)
    create_parser.add_argument('--continue', dest='continue_creation', help="Continue a previously interrupted corpora creation process. A 'processed-articles-lang.temp' file should exist in the corpus directory.", action='store_true', required=False)
    create_parser.set_defaults(func=create_corpora)

# SEGMENT SUBPARSER
    segment_parser = subparsers.add_parser("segment", help="Segment the extracted corpus.", description="Segment all text files in a folder. The folder name must contain a language code at the end separated by a hyphen from the rest. If you have created a corpus using the 'create' command, this folder is named 'pages-en'. The output is a 'segments' folder and a 'unique-segments' text file with the language ISO code at the end.")
    segment_parser.add_argument("indir", help="Folder where the corpus to segment is stored, e.g., 'pages-en'. The name must contain a hyphen and a language code at the end.")
    segment_parser.add_argument("--srxfile", type=str, help="The SRX file to use. Default: segment.srx", required=False)
    segment_parser.add_argument("--force-srx-lang", help="Override the default SRX language configuration if your language is not available in the file. You may use one of the following: Default, Generic, ByLineBreak or ByTwoLineBreaks.", required=False)
    segment_parser.add_argument("--force-segmenter", help="Use a Stanza sentence segmenter instead of SRX. Note that it is slower than the SRX implementation, but useful if your language is supported in this library and not in the SRX file.", required=False, action="store_true")
    segment_parser.add_argument("--chunk", help="Compile the whole corpus in chunks before segmenting. If the corpus is made up of millions of files, the time saved is massive. Note that individual segmented articles will not be available.", action="store_true", required=False)
    segment_parser.add_argument("--outdir", type=str, help="Output directory in which to save the segmented files. If not specified, it will be saved in the same directory as the input file.", required=False)
    segment_parser.set_defaults(func=segment_corpus)

# ALIGN SUBPARSER
    align_parser = subparsers.add_parser("align", help="Perform bitext mining and alignment between two corpora.", description="Bitext mine and align parallel sentences from two lists of monolingual sentences. The input directory can be a folder where both corpora are located, e.g. corpus-ca-en/ if your aim is to create a parallel corpus, or two different folders (e.g. corpus-en/ corpus-ca/). The tool automatically looks for the unique segments files in both languages. The output is an aligned segments text file.")
    align_parser.add_argument("indir", help="Path to the folder that contains the unique segments files (e.g. corpus-en-ca/).")
    align_parser.add_argument("optional_indir", nargs='?', help="Use this argument too if you are aligning two monolingual corpora, that is, they are located in separate folders (e.g. monolingual/corpus-en/ monolingual/corpus-ca/).", default=None)
    align_parser.add_argument("-dev", "--device", choices=["gpu", "cpu"], default="gpu", dest="device", help="Device used (GPU or CPU). Default: GPU.", required=False)
    align_parser.add_argument("--mode", type=str, choices=["safe", "balanced", "fast"], default="safe", help="Preset performance mode for computation of embeddings. 'safe' is meant for consumer hardware (8GB VRAM). 'balanced' is meant for workstations (24GB VRAM). 'fast' is meant for high-performance computing servers (80GB+ VRAM). Default: safe.")
    align_parser.add_argument("--outdir", help="Output directory in which to save the aligned segments files. If not specified, it will be saved in the same directory as the input file.", required=False)
    align_parser.set_defaults(func=align_corpora)

# RESCORE SUBPARSER
    rescore_parser = subparsers.add_parser("rescore", help="Rescore the alignment using more computationally expensive models.", description="Rescore previously aligned corpora. The aligned segments are evaluated using more computationally expensive models. The output file is a rescored segments text file.")
    rescore_parser.add_argument("indir", help="Path to the folder that contains an aligned segments file.")
    rescore_parser.add_argument("--SEmodel", help="Sentence Transformers embeddings model. Default model: LaBSE", required=False)
    rescore_parser.add_argument("--LDmodel", help="The fastText language detection model. Default model: lid.176.bin", required=False)
    rescore_parser.add_argument("--outdir", help="Output directory in which to save the rescored segments file. If not specified, it will be saved in the same directory as the input file.")   
    rescore_parser.set_defaults(func=rescore_corpus)

# SELECT SUBPARSER
    select_parser = subparsers.add_parser("select", help="Filter the rescored parallel segments.", description="Filter the rescored segments based on the defined quality thresholds. The input file should be a text file of rescored segments containing the ISO language codes, e.g.: 'rescored-segments-en-es.txt'. The output file is a selected segments text file.")
    select_parser.add_argument("indir", help="Path to the folder that contains a rescored segments file.  This file is meant to be the resulting one from the rescore function")
    select_parser.add_argument("--sldc", type=float, help="The minimum source language detection confidence. Default value is 0.75", required=False, default=0.75)
    select_parser.add_argument("--tldc", type=float, help="The minimum target language detection confidence. Default value is 0.75", required=False, default=0.75)
    select_parser.add_argument("--minSBERT", type=float, help="The minimum value for SBERT cosine similarity score to select a segment pair. Default value is 0.75", required=False, default=0.75)
    select_parser.add_argument("--min-chars", type=int, help="Minimum character length of selected segments. By default, segments of any length are selected. Short segments can be ignored using this flag.  Default: 0.", required=False)
    select_parser.add_argument("--outdir", type=str, help="Output directory in which to save the selected segments file. If not specified, it will be saved in the same directory as the input file.")
    select_parser.set_defaults(func=select_corpus)

# PIPELINE SUBPARSER
    pipeline_parser = subparsers.add_parser("pipeline", help="Execute the whole pipeline: create > segment > align > rescore > select", formatter_class=argparse.RawDescriptionHelpFormatter, description=
    ''' Run the following pipeline:

        1. Create parallel corpora from Wikipedia dumps.
        2. Segment the content of both corpora in sentences.
        3. Perform bitext mining (alignment) on both corpora.
        4. Rescore the corpora.
        5. Filter the rescored parallel segments. ''')
    
    pipeline_parser.add_argument('lang1', help='Name or two letter ISO code of the source language.')
    pipeline_parser.add_argument('lang2', help='Name or two letter ISO code of the target language.')
    pipeline_parser.add_argument("--outdir", help="Name of the output directory, default is: corpora. Language codes will be added after it, i.e.: corpora-lang1-lang2/", required=False)
    
    # CREATE OPTIONS
    create_group = pipeline_parser.add_argument_group("Create options")
    create_group.add_argument('-c', '--categories', action="store", help='Wikipedia categories to search. Must be in between quotation marks ("") and separated by a comma (,). If no categories are passed, the whole dump will be processed.', required=False)
    create_group.add_argument('-d', '--depth', type=int, help='Recursion depth for traversing the category tree.', required=False)
    create_group.add_argument('--restrict', action='store_true', help='Restrict L2 pages to equivalent L1 pages.', required=False)
    create_group.add_argument("--database", help='The CCW sqlite database to use. Default: database/CCWikipedia-20251201.sqlite', required=False)
    create_group.add_argument('--dumps', help='Wikipedia dumps path. Default: dumps/',required=False)

    # SEGMENT OPTIONS
    segment_group = pipeline_parser.add_argument_group("Segment options")
    segment_group.add_argument("--srxfile", type=str, help="The SRX file to use. Default: segment.srx", required=False)
    segment_group.add_argument("--force-srx-lang", help="Override the default SRX language configuration if your language is not available in the file. You may use one of the following: Default, Generic, ByLineBreak or ByTwoLineBreaks. Can choose between src and tgt, e.g. 'src Default'",nargs=2, metavar=("SIDE", "LANG"), action="append", required=False)
    segment_group.add_argument("--force-segmenter", help="Use a Stanza sentence segmenter instead of SRX. Note that it is slower than the SRX implementation, but useful if your language is supported in this library and not in the SRX file. Can choose between src and tgt.", required=False, choices=["src", "tgt"], nargs="+")
    segment_group.add_argument("--chunk", help="Compile the whole corpus in chunks before segmenting. If the corpus is made up of millions of files, the time saved is massive. Note that individual segmented articles will not be available.", action="store_true", required=False)

    # ALIGN OPTIONS
    align_group = pipeline_parser.add_argument_group("Align options")
    align_group.add_argument("optional_indir", nargs='?', help="Use this argument too if you are aligning two monolingual corpora, that is, they are located in separate folders (e.g. monolingual/corpus-en/ monolingual/corpus-ca/).", default=None)
    align_group.add_argument("-dev", "--device", choices=["gpu", "cpu"], default="gpu", dest="device", help="Device used (GPU or CPU). Default: GPU.", required=False)
    align_group.add_argument("--mode", type=str, choices=["safe", "balanced", "fast"], default="safe", help="Preset performance mode for computation of embeddings. 'safe' is meant for consumer hardware (8GB VRAM). 'balanced' is meant for workstations (24GB VRAM). 'fast' is meant for high-performance computing servers (80GB+ VRAM). Default: safe.")

    # RESCORE OPTIONS
    rescore_group = pipeline_parser.add_argument_group("Rescore options")
    rescore_group.add_argument("--SEmodel", help="Sentence Transformers embeddings model. Default model: LaBSE", required=False)
    rescore_group.add_argument("--LDmodel", help="The fastText language detection model. Default model: lid.176.bin", required=False)

    # SELECT OPTIONS
    select_group = pipeline_parser.add_argument_group("Select options")
    select_group.add_argument("--sldc", type=float, help="The minimum source language detection confidence. Default value is 0.75", required=False, default=0.75)
    select_group.add_argument("--tldc", type=float, help="The minimum target language detection confidence. Default value is 0.75", required=False, default=0.75)
    select_group.add_argument("--minSBERT", type=float, help="The minimum value for SBERT cosine similarity score to select a segment pair. Default value is 0.75", required=False, default=0.75)
    select_group.add_argument("--min-chars", type=int, help="Minimum character length of selected segments. By default, segments of any length are selected. Short segments can be ignored using this flag.  Default: 0.", required=False)

    pipeline_parser.set_defaults(func=pipeline)

# DATABASE SUBPARSER
    database_parser = subparsers.add_parser("database", help="Generate a categories database.", description="Generate a categories database to be used by the 'create' command.")
    database_parser.add_argument("--skoscategories", help="The skos_categories_CODE.ttl.bz2 file. Can be downloaded from https://downloads.dbpedia.org/", required=True, dest="skos")
    database_parser.add_argument("--langlinks", help="The CODE-langlinks.sql.gz file. Can be downloaded from https://dumps.wikimedia.org/backup-index.html", required=True, dest="lang_links")
    database_parser.add_argument("--dump", help="The path to the dump to be used.", required=True, dest="dump")
    database_parser.add_argument("--outdir", type=str, help="Output directory where to save the generated database. Default is in the tool's folder.")
    database_parser.set_defaults(func=generate_database)

# parsing all args
    args = parser.parse_args() 
    args.func(args)

if __name__ == "__main__":

    cli()