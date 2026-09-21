# corpus-from-wikipedia
`corpus-from-wikipedia` is a CLI tool that can create specialized monolingual and parallel corpora from Wikipedia. The generated corpora are intended to train and evaluate domain-specific machine translation systems.

The tool makes use of Wikipedia categories and the articles that form part of them to compile a corpus. You can read further below for more information on how to use the tool.

This CLI unifies several previously standalone scripts into a single tool, while adding a new `pipeline` command to chain them together. Each command contains the source in their description further below.

## How to install the tool 
1. Clone the tool:  
`git clone https://github.com/grial-research-group/corpus-from-wikipedia.git` 
2. Create a virtual or conda environment. Afterwards, open the directory of the repo in your terminal and install the tool in editable mode:  
`pip install -e .`
3. The tool is now installed and can be used in your terminal with the commands `corpus-from-wikipedia` or simply `cfw`.

For the tool to work, you need a **Wikipedia dump** and a **categories database**. The **dumps** can be downloaded from [here](https://dumps.wikimedia.org/backup-index-bydb.html). The name of the **dumps** is the two letter ISO language code followed by 'wiki', e.g., *cawiki* for the Catalan Wikipedia. Once found, you need to download the file '*pages-articles.xml.bz2*'. We provide a recent **database** in [this](https://huggingface.co/datasets/gon-zalo/cfw-database/tree/main) link, but a new one can be generated with the command `database`. Both these files need to be placed in the `dumps` and `database` folders respectivelly. 


## Getting started

First, try typing in your terminal the command, using the help flag, to ensure it was installed.

```console
$ cfw -h
usage: cfw [-h] {create,segment,align,rescore,select,pipeline,database} ...

Tool to create specialized monolingual and parallel corpora from Wikipedia. It supports step-by-step 
execution and full pipeline execution. That is, commands may be run individually, e.g., in order to 
inspect results between steps, or execute the entire workflow at once using the 'pipeline' command.

positional arguments:
  {create,segment,align,rescore,select,pipeline,database}
    create              Create a corpus from Wikipedia.
    segment             Segment the extracted corpus.
    align               Perform bitext mining and alignment between two corpora.
    rescore             Rescore the alignment using more computationally expensive models.
    select              Filter the rescored parallel segments.
    pipeline            Execute the whole pipeline: create > segment > align > rescore > select
    database            Generate a categories database.

options:
  -h, --help            show this help message and exit
```

The tool consists mainly of six subcommands: `create`, `segment`, `align`, `rescore`, `select`, and `pipeline`. Each phase of the corpus creation process can be run independently, permitting the inspection of intermediate outputs before proceeding to the subsequent stages. Alternatively, the whole process can be executed in a single run by using the `pipeline` subcommand. The last command, `database` is used to generate a categories database.

You can run each command with the help flag (`-h`) to see in detail the functionalities of each command and its parameters.

The `create` command will create a folder named `corpus` by default, followed by the source language ISO code and the target language ISO code, e.g. `corpus-ca-en`. It is recommended to keep all files of the subsequent commands in the same folder, although the output path can be changed.

### Create

Creates a corpus from Wikipedia dumps. Based on https://github.com/mtuoc/MTUOC-corpusFromWikipedia. The `create` command contains the following parameters:

- `lang1`                 Name or ISO code of the source language.
- `lang2`                 Name or ISO code of the target language. Keep empty to create a monolingual corpus.

Optional:
-  `-c` or `--categories`: 
                        Wikipedia categories to search. Must be in between quotation marks ("") and separated by a
                        comma (,). Category names can be looked up [here](https://en.wikipedia.org/wiki/Wikipedia:Contents/Categories) in advance.
-  `-d` DEPTH, `--depth`: 
                        Recursion depth for traversing the category tree.
-  `--restrict`:            Restrict L2 pages to equivalent L1 pages.
- `--database`:   The directory where the CCW SQLite database is. Default: database/
- `--dumps`:         Wikipedia dumps path. Default: dumps/
- `--outdir`:        Name of the output directory. Default: corpora-lang1-lang2/. Language codes will be added
                        automatically.
- `--continue`:            Continue a previously interrupted corpora creation process. A 'processed-articles-lang.temp'
                        file should exist in the corpus directory.

Example:

`cfw create ca en -c "Marine biology" -d 2 --restrict --outdir marine`

This command will get the articles in the Wikipedia category [Marine Biology](https://en.wikipedia.org/wiki/Category:Marine_biology) in Catalan and in English with a depth of two. The English ones will be restricted to only those that exist in the Catalan Wikipedia. The resulting folder will be named `marine-ca-en.`

### Segment

Segments all text files in a `pages` folder. Based on https://github.com/mtuoc/MTUOC-segmenter. The `segment` command contains the following parameters:

-  `indir`:                 Folder where the corpus to segment is stored, e.g., 'pages-en'. The name must contain a hyphen
                        and a language code at the end.

Optional:
-  `--srxfile`:     The SRX file to use. Default: segment.srx
-  `--force-srx-lang`:
                        Override the default SRX language configuration if your language is not available in the file.
                        You may use one of the following: Default, Generic, ByLineBreak or ByTwoLineBreaks.
-  `--force-segmenter`:     Use a Stanza sentence segmenter instead of SRX. Note that it is slower than the SRX
                        implementation, but useful if your language is supported in this library and not in the SRX
                        file.
-  ``--chunk``:               Compile the whole corpus in chunks before segmenting. If the corpus is made up of millions of
                        files, the time saved is massive. Note that individual segmented articles will not be
                        available.
-  ``--outdir``:       Output directory in which to save the segmented files. If not specified, it will be saved in
                        the same directory as the input file.

Example:

`cfw segment corpora/parallel/marine-ca-en/pages-ca/ --chunk`

### Align
Bitext mines and aligns parallel sentences from two lists of monolingual sentences. Based on https://github.com/mtuoc/MTUOC-aligner. The `align` command contains the following parameters:

-  `indir`                 Path to the folder that contains the unique segments files (e.g. corpus-
                        en-ca/).
-  `optional_indir`        Use this argument too if you are aligning two monolingual corpora, that
                        is, they are located in separate folders (e.g. monolingual/corpus-en/
                        monolingual/corpus-ca/).

Optional:  
-  `-dev`, `--device`: Device used (GPU or CPU). Default: GPU.
-  `--mode`: Preset performance mode for computation of embeddings. 'safe' is meant for
                        consumer hardware (8GB VRAM). 'balanced' is meant for workstations (24GB
                        VRAM). 'fast' is meant for high-performance computing servers (80GB+
                        VRAM). Default: safe.
-  `--outdir`: Output directory in which to save the aligned segments files. If not
                        specified, it will be saved in the same directory as the input file.

Example:

`cfw align corpora/parallel/marine-ca-en/ --mode fast`

### Rescore

Rescores previously aligned corpora. Based on https://github.com/mtuoc/MTUOC-PCorpus-rescorer. The aligned segments are evaluated using more computationally expensive models. The `rescore` command contains the following parameters:


-  indir              Path to the folder that contains an aligned segments file.

Optional:
-  `--SEmodel`: Sentence Transformers embeddings model. Default model: `LaBSE`.
-  `--LDmodel`: The fastText language detection model. Default model: `lid.176.bin`.
-  `--outdir`: Output directory in which to save the rescored segments file. If not specified, it will
                     be saved in the same directory as the input file.

Example:

`cfw rescore corpora/parallel/marine-ca-en/`

### Select

Filters the rescored segments based on the defined quality thresholds. Based on https://github.com/mtuoc/MTUOC-PCorpus-rescorer. The `select` command contains the following parameters:

-  `indir`                 Path to the folder that contains a rescored segments file. This file is meant to be
                        the resulting one from the rescore function

`Optional`:
-  `--sldc`: The minimum source language detection confidence. Default value is 0.75.
-  `--tldc`: The minimum target language detection confidence. Default value is 0.75.
-  `--minSBERT`: The minimum value for SBERT cosine similarity score to select a segment pair. Default
                        value is 0.75.
-  `--min-chars`: Minimum character length of selected segments. By default, segments of any length are selected. Short segments can be ignored using this flag. Default: 0.
-  `--outdir`: Output directory in which to save the selected segments file. If not specified, it
                        will be saved in the same directory as the input file.

Example:

`cfw select corpora/parallel/marine-ca-en/ --min-chars 25`

### Pipeline

Runs all the previous commands in one go. It supports all parameters of each individual command directly on the same command line.

Example:

`cfw pipeline ca en -c "Marine biology" -d 2 --restrict --outdir marine --chunk --mode fast --min-chars 25`

## Database creation

Generate a categories SQLite database. Based on https://github.com/mtuoc/MTUOC-corpusFromWikipedia. The `database` command contains the following parameters:

-  `--skoscategories`: The skos_categories_CODE.ttl.bz2 file. Can be downloaded from https://downloads.dbpedia.org/
-  `--langlinks`: The CODE-langlinks.sql.gz file. Can be downloaded from https://dumps.wikimedia.org/backup-index.html
-  `--dump`: The path to the dump to be used. Can be downloaded from https://dumps.wikimedia.org/backup-index.html.
-  `--outdir`: Output directory where to save the generated database. Default is in the tool's folder.

See [How to install the tool](#how-to-install-the-tool) for more information.