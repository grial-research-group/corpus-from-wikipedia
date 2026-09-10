#!/usr/bin/python3
#   Copyright (C) 2024  Antoni Oliver
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.

#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see <https://www.gnu.org/licenses/>.

def select_corpus(args):
    from pathlib import Path
    print("\nRunning select command")

    indir = args.indir
    outdir = args.outdir

    indir = Path(indir)

    outdir = outdir or indir
    outdir = Path(outdir)
    min_chars = args.min_chars or 0

    file_codes = ''
    print("")
    for file in indir.iterdir():
        if file.is_file() and file.name.startswith("rescored-segments"):
            print(f"Rescored segments file {file.name} found")
            stem = file.stem
            stem = stem.split("-")
            sl = stem[-2]
            tl = stem[-1]
            file_codes = f'{sl}-{tl}' # getting both language codes from the file name
            input_file = file
    print("")
    output_file = outdir / f'selected-segments-{file_codes}.txt'

    sldc = args.sldc
    tldc = args.tldc
    minSBERT = args.minSBERT

    if minSBERT == None:
        minSBERT = -1000000
    else:
        minSBERT = float(minSBERT)

    sortida=open(output_file,"w",encoding="utf-8")
    entrada=open(input_file,"r",encoding="utf-8")

    segment_count = 0

    for linia in entrada:
        linia=linia.rstrip()
        camps=linia.split("\t")
        slsegment=camps[0]
        tlsegment=camps[1]
        slinfolangs=camps[2]
        slinfolang1=slinfolangs.split(";")[0]
        sllang=slinfolang1.split(":")[0]
        slconf=float(slinfolang1.split(":")[1])
        
        tlinfolangs=camps[3]
        tlinfolang1=tlinfolangs.split(";")[0]
        tllang=tlinfolang1.split(":")[0]
        tlconf=float(tlinfolang1.split(":")[1])
        
        sbert=float(camps[4])
        
        if sllang==sl and slconf>=sldc and tllang==tl and tlconf>=tldc and sbert>=minSBERT and len(slsegment) >= min_chars and len(tlsegment) >= min_chars:
            cadena=f"{slsegment}\t{tlsegment}"
            segment_count += 1
            sortida.write(f"{cadena}\n")

    print(f'{segment_count} segments saved')