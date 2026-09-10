#!/usr/bin/python3
# Copyright (C) 2025  Antoni Oliver
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

def process(sources, targets, scores, sortida, SEmodel, LDmodel):
    from sentence_transformers import util

    SEmodel = SEmodel
    LDmodel = LDmodel
    embeddings1 = SEmodel.encode(sources, convert_to_tensor=False)
    embeddings2 = SEmodel.encode(targets, convert_to_tensor=False)
    cosine_scores = util.cos_sim(embeddings1, embeddings2)

    for i in range(len(sources)):
        try:
            source = sources[i]
            target = targets[i]
            score = float(scores[i]) if scores[i] != 0 else 0.0
            cosine_score = cosine_scores[i][i].item()
            
            # Language detection predictions
            DL1 = LDmodel.predict(source, k=5)
            DL2 = LDmodel.predict(target, k=5)
            
            # Validate DL1 and DL2 have enough predictions
            if len(DL1[0]) < 1 or len(DL2[0]) < 1:
                print(f"WARNING: Insufficient labels for line {i}")
                continue
            
            predL1 = []
            for j in range(len(DL1)-1):
                L1 = DL1[0][j].replace("__label__", "")
                confL1 = float(DL1[1][j])
                predL1.append(f"{L1}:{confL1}")
            predL1 = ";".join(predL1)

            predL2 = []
            for j in range(len(DL2)-1):
                L2 = DL2[0][j].replace("__label__", "")
                confL2 = float(DL2[1][j])
                predL2.append(f"{L2}:{confL2}")
            predL2 = ";".join(predL2)

            # Write the output line
            cadena = f"{source}\t{target}\t{predL1}\t{predL2}\t{cosine_score}"
            sortida.write(cadena + "\n")

        except Exception as e:
            print(f"ERROR processing line {i}: {e}")

def rescore_corpus(args):
    print("\nRunning rescore command")
    import fasttext
    from sentence_transformers import SentenceTransformer
    import urllib
    from pathlib import Path

    indir = args.indir
    outdir = args.outdir

    indir = Path(indir)

    outdir = outdir or indir
    outdir = Path(outdir)
    tool_folder = Path(__file__).parent.parent.parent

    # looking for aligned-segments file
    file_codes = ''
    print("")
    for file in indir.iterdir():
        if file.is_file() and file.name.startswith("aligned-segments"):
            print(f"Aligned segments file {file.name} found")
            stem = file.stem
            stem = stem.split("-")
            file_codes = f'{stem[-2]}-{stem[-1]}' # getting both language codes from the file name
            input_file = file
    print("")
    output_file = outdir / f'rescored-segments-{file_codes}.txt'

    SEmodel_default = "LaBSE"
    LDmodel_default = "lid.176.bin"
    LDmodel_default_path = tool_folder / LDmodel_default
    LDmodel_default_url = 'https://dl.fbaipublicfiles.com/fasttext/supervised-models/lid.176.bin'

    if args.SEmodel:
        SEmodel = args.SEmodel
    else:
        SEmodel = SEmodel_default

    if args.LDmodel:
        LDmodel = args.LDmodel
        LDmodel_path = Path(LDmodel)
    else:
        LDmodel = LDmodel_default
        LDmodel_path = LDmodel_default_path

    maxlines = 10000

    if LDmodel_path.exists():
        try:
            LDmodel = fasttext.load_model(str(LDmodel_path))
            print("Language detection model loaded successfully")
        except Exception as e:
            print(f"Error loading model: {e}")
    else:
        print(f"Model not found in path {LDmodel_path}")
        print("Downloading default model")
        try:
            LDmodel_path.parent.mkdir(parents=True, exist_ok=True)
            urllib.request.urlretrieve(LDmodel_default_url, str(LDmodel_path))
            LDmodel = fasttext.load_model(LDmodel)
            print("Language detection model downloaded and loaded successfully")
        except Exception as e:
            print(f"Error downloading model: {e}")

    SEmodel = SentenceTransformer(SEmodel)
    print("\nSentence embeddings model loaded successfully\n")

    entrada = open(input_file,"r",encoding="utf-8")
    sortida = open(output_file,"w",encoding="utf-8")

    cont = 0
    cont2 = 0
    sources = []
    targets = []
    scores = []

    for linia in entrada:
        linia=linia.rstrip()
        camps=linia.split("\t")
        try:
            sources.append(camps[0])
            targets.append(camps[1])
            if len(camps)>=3:
                scores.append(camps[2])
            else:
                scores.append(0)
        except:
            pass
        cont+=1
        if cont%maxlines==0:
            print("CONT: ",cont2*maxlines)
            cont2+=1
        if cont==maxlines:
            process(sources,targets,scores,sortida, SEmodel, LDmodel)
            cont=0
            sources=[]
            targets=[]
            scores=[]
    process(sources,targets,scores,sortida, SEmodel, LDmodel)

    entrada.close()
    sortida.close()

    print(f'Segments rescored saved to {sortida.name}')