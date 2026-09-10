from ..utils.get_language import get_language
from .create import create_corpora
from .segment import segment_corpus
from .align import align_corpora
from .rescore import rescore_corpus
from .select import select_corpus
from pathlib import Path
import argparse

def pipeline(args):
    print("Running pipeline command")

    outdir = args.outdir
    lang1 = args.lang1
    lang2 = args.lang2

    lang1_name, lang1_code = get_language(lang1)
    lang2_name, lang2_code = get_language(lang2)

    outdir = outdir or 'corpus'
    current_dir = Path.cwd()
    outputs_folder = current_dir / "corpora" / "parallel"
    corpora_folder = outputs_folder / f'{outdir}-{lang1_code}-{lang2_code}'

    print(f"\nCreating parallel corpus in {lang1_name} and {lang2_name}")

    # create args
    database = args.database
    
    dumps = args.dumps
    categories = args.categories
    level = args.depth
    restrict = args.restrict
    
    # create corpora
    create_args = argparse.Namespace(
        database=database, 
        lang1=lang1_code, 
        lang2=lang2_code, 
        dumps=dumps, 
        categories=categories, 
        depth=level, 
        restrict=restrict,
        outdir=outdir,
        continue_creation=False)
    create_corpora(create_args)


    # segment args
    srxfile = args.srxfile
    
    forced_srx = {}
    for side, lang in args.force_srx_lang or []:
        forced_srx[side] = lang

    src_srx = forced_srx.get("src")
    tgt_srx = forced_srx.get("tgt")
    src_segmenter = False
    tgt_segmenter = False
    if args.force_segmenter:
        if "src" in args.force_segmenter:
            src_segmenter = True

        if "tgt" in args.force_segmenter:
            tgt_segmenter = True

    chunk = args.chunk

    # segment corpora
    src_args = argparse.Namespace(
        srxfile=srxfile,  
        force_srx_lang=src_srx,
        force_segmenter=src_segmenter,
        chunk=chunk,
        indir=corpora_folder / f"pages-{lang1_code}",
        outdir=corpora_folder)
    segment_corpus(src_args)

    tgt_args = argparse.Namespace(
        srxfile=srxfile,  
        force_srx_lang=tgt_srx,
        force_segmenter=tgt_segmenter,
        chunk=chunk,
        indir=corpora_folder / f"pages-{lang2_code}",
        outdir=corpora_folder,
        running_pipeline=True,
        lang_code=lang2_code)
    segment_corpus(tgt_args)


    # align args
    device = args.device
    optional_indir = args.optional_indir
    mode = args.mode
    # align segments
    align_args = argparse.Namespace(
        device=device, 
        indir=corpora_folder,
        outdir=corpora_folder,
        optional_indir=optional_indir,
        mode=mode)
    align_corpora(align_args)


    # rescore args
    SEmodel = args.SEmodel
    LDmodel = args.LDmodel

    # rescore segments
    rescore_args = argparse.Namespace(
        indir= corpora_folder, 
        SEmodel=SEmodel, 
        LDmodel=LDmodel,
        outdir= corpora_folder)
    rescore_corpus(rescore_args)


    # select args
    sldc = args.sldc
    tldc = args.tldc
    minSBERT = args.minSBERT
    min_chars = args.min_chars

    # select segments
    select_args = argparse.Namespace(
        indir=corpora_folder, 
        sldc=sldc, 
        tldc=tldc, 
        minSBERT=minSBERT,
        min_chars=min_chars,
        outdir=corpora_folder)
    select_corpus(select_args)
