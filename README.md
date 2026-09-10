# corpus-from-wikipedia
`corpus-from-wikipedia` is a CLI tool that can create specialized monolingual and parallel corpora from Wikipedia. The generated corpora are intended to train and evaluate domain-specific machine translation systems.

The tool makes use of Wikipedia categories and the articles that form part of them, to compile a corpus. You can read further below for a short tutorial on how to use the tool.

## How to install the tool 
1. Clone the tool:  
`git clone https://github.com/grial-research-group/corpus-from-wikipedia.git` 
2. Create a virtual or conda environment. Afterwards, open the directory of the repo in your terminal and install the tool in editable mode:  
`pip install -e .`
3. The tool is now installed and can be used in your terminal with the commands `corpus-from-wikipedia` or simply `cfw`.

For the tool to work, you need a Wikipedia dump and a categories database. The dumps can be downloaded from [here](https://dumps.wikimedia.org/backup-index-bydb.html). The name of the dumps is the two letter ISO language code followed by 'wiki', e.g., *cawiki* for the Catalan Wikipedia. Once found, you need to download the '*pages-articles.xml.bz2*'. The database...

These files need to be placed in the `dumps` and `database` folders respectivelly. 

You can run each command with the help flag (`-h`) to see in detail the functionalities of each command and its parameters.