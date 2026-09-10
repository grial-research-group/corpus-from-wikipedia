# corpus-from-wikipedia
`corpus-from-wikipedia` is a CLI tool that can create specialized monolingual and parallel corpora from Wikipedia. The generated corpora are intended to train and evaluate domain-specific machine translation systems.

The tool makes use of Wikipedia categories and the articles that form part of them, to compile a corpus. You can read further below for a short tutorial on how to use the tool.

## How to install the tool 
1. Clone the tool:  
`git clone https://github.com/grial-research-group/corpus-from-wikipedia.git` 
2. Create a virtual or conda environment. Afterwards, open the directory of the repo in your terminal and install the tool in editable mode:  
`pip install -e .`
3. The tool is now installed and can be used in your terminal with the commands `corpus-from-wikipedia` or simply `cfw`.

For the tool to work, you need a Wikipedia dump and a categories database. The dumps can be downloaded from [here](https://dumps.wikimedia.org/backup-index-bydb.html). The name of the dumps is the two letter ISO language code followed by 'wiki', e.g., *cawiki* for the Catalan Wikipedia. Once found, you need to download the '*pages-articles.xml.bz2*'. The database... These files need to be placed in the `dumps` and `database` folders respectivelly. 

## Geting started

First, try typing in your terminal the command, using the help flag, to ensure it was installed

```console
$ cfw -h
usage: cfw [-h] {create,segment,align,rescore,select,pipeline,database} ...

Tool to create specialized monolingual and parallel corpora from Wikipedia. It supports step-by-step execution and full pipeline execution. That is, commands may be run individually, e.g., in order to inspect results between steps, or execute the entire workflow at once using the 'pipeline' command.

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

As we can see in the terminal output, the tool contains seven subcommands: `create`, `segment`, `align`, `rescore`, `select`, `pipeline` and `database`. Each phase can be run independently, permitting the inspection of intermediate outputs before proceeding to the subsequent stages. Alternatively, the whole process can be executed in a single run by using the `pipeline` subcommand.

You can run each command with the help flag (`-h`) to see in detail the functionalities of each command and its parameters.