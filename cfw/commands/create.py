#!/usr/bin/python3
# Copyright (C) 2021  Antoni Oliver
# Copyright (C) 2026  Gonzalo López-Sánchez
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

def extract_text_from_wikitext(wikitext):
    import mwparserfromhell
    wikicode = mwparserfromhell.parse(wikitext)
    return wikicode.strip_code()
    
def find_dump(dumps_path, lang_code, lang_name):
    import sys
    dump = next(dumps_path.glob(f'{lang_code}*'), None)
    if dump:
        print(f'Dump in {lang_name} found: {str(dump)}')
    else:
        print(f'{lang_name} dump not found in directory.')
        sys.exit()

    return dump

def find_database(database_folder):
    suffixes = (".sqlite", ".database", ".db")

    database = next((f for f in database_folder.iterdir() if f.suffix in suffixes), None)

    if not database:
        raise RuntimeError("Database not found")

    else:
        print(f"Database {database} found")

    return database

def check_necessary_folders(tool_folder, args):
    from pathlib import Path

    if args.database:
        database_folder = args.database
    else:
        database_folder = tool_folder / "database"

    if args.dumps:
        dumps_folder = args.dumps
    else:
        dumps_folder = tool_folder / "dumps"

    database_folder = Path(database_folder)
    dumps_folder = Path(dumps_folder)

    if database_folder.is_dir() and dumps_folder.is_dir():

        return database_folder, dumps_folder

    else:
        raise RuntimeError("Database and/or dumps folder do not exist in the tool's directory.")
    
def create_corpora(args):
    import sqlite3
    import mwxml
    import bz2
    from pathlib import Path
    import os
    import sys
    import re
    from tqdm import tqdm
    from ..utils.get_language import get_language
    from ..utils.category_namespaces import fetch_category_namespaces
    print("\nRunning create command")

    category_namespaces = fetch_category_namespaces()
    lang1 = args.lang1
    lang2 = args.lang2
    current_directory = Path.cwd()
    tool_folder = Path(__file__).parent.parent.parent
    database_folder, dumps_folder = check_necessary_folders(tool_folder=tool_folder, args=args)
    database = find_database(database_folder=database_folder)

    corpora_folder = current_directory / "wikipedia-corpora"
    corpora_folder.mkdir(parents=True, exist_ok=True)
    
    continue_creation = args.continue_creation
    outdir = args.outdir if args.outdir else None

    if lang2: # if bilingual
        print("Creating bilingual corpus\n")
        lang1_name, lang1_code = get_language(lang1)
        lang2_name, lang2_code = get_language(lang2)
        langs = [lang1_code, lang2_code]

        dumpL1 = find_dump(dumps_folder, lang1_code, lang1_name)
        dumpL2 = find_dump(dumps_folder, lang2_code, lang2_name)

        if not outdir:
            outdir = corpora_folder / "parallel" / f"corpus-{lang1_code}-{lang2_code}"
        else:
            outdir = corpora_folder / "parallel" / f"{outdir}-{lang1_code}-{lang2_code}"

    else: # if monolingual
        print("Creating monolingual corpus")
        lang1_name, lang1_code = get_language(lang1)
        langs = [lang1_code]

        dumpL1 = find_dump(dumps_folder, lang1_code, lang1_name)

        if not outdir:
            outdir = corpora_folder / "monolingual" / f"corpus-{lang1_code}"
        else:
            outdir = corpora_folder / "monolingual" / f"{outdir}-{lang1_code}"

    if outdir.exists() and not continue_creation:
        raise RuntimeError("Directory already exists, choose another name")

    elif not outdir.exists() and not continue_creation:
        outdir.mkdir(parents=True)
        print(f"Created folder: {outdir}")

    elif outdir.exists() and continue_creation:
        print(f"{outdir} found. The creation of the corpus will continue.")
    
    categories = args.categories
    
    conn = sqlite3.connect(database)
    cur = conn.cursor() 
    selectcategories = False
    whole_dump = False if categories else True

    if categories: # if you want to fetch specific categories
        level = args.depth
        if categories and not level:
            raise RuntimeError("'--depth' is required when passing categories")

        categories_list = []
        categoriesTEMP = []

        for cat in categories.split(","):
            cat = cat.strip()
            categories_list.append(cat)
            categoriesTEMP.append(cat)
        categoriesAUX=[]

        while level>0:
            while(len(categoriesTEMP))>0:
                categories=categoriesTEMP.pop(0)
                cur.execute('SELECT categoryREL from categoryrelations WHERE category=?', (categories,))
                data=cur.fetchall()
                if data:
                    for d in data:
                        categories_list.append(d[0])
                        categoriesAUX.append(d[0])
            categoriesTEMP.extend(categoriesAUX)
            categoriesAUX=[]
            level-=1

        selectcategories=True


    restrict = args.restrict
    contlang=0
    restrictedIdentsKeys=[]

    cat_without_data= []
    for lang in langs:
        lang_name, lang_code = get_language(lang)

        contlang += 1
        idents={}
        
        article_list="articlelist-"+lang_code+".txt"
        article_list_path = os.path.join(outdir, article_list)
        article_list_file = open(article_list_path,"w",encoding="utf-8")
        
        if contlang==2 and restrict:
            selectcategories=False

        if selectcategories:
            for category in categories_list:
                cur.execute('SELECT ident from categories WHERE category=?', (category,))
                data = cur.fetchall()
                if data:
                    for d in data:
                        idents[d[0]]=1
                if not data and contlang == 1:
                    cat_without_data.append(category)

            categories_list = [cat for cat in categories_list if cat not in cat_without_data]
            if len(categories_list) == 0:
                raise ValueError("No categories detected.")
            if contlang == 1:
                print(f"Total categories found: {len(categories_list)}")

        elif whole_dump: # parse the whole dump
            print("No categories selected. The whole dump will be processed.")
            cur.execute('SELECT ident FROM titles')
            data = cur.fetchall()
            for d in data:
                idents[d[0]] = 1

        print(f"Fetching article names in {lang_name}")
        if restrict and contlang==2:
            identskeys=restrictedIdentsKeys
        else:
            identskeys=idents.keys()
    
        todownload=[]
        
        if contlang==1:
            restrictedIdentsKeys=[]

        if not lang_code=="en":
            for ident in identskeys:
                cur.execute('SELECT title from langlinks WHERE ident=? and lang=?', (ident,lang_code))
                data=cur.fetchone()
                if not data==None:
                    if contlang==1: restrictedIdentsKeys.append(ident)
                    todownload.append(data[0])
                    article_list_file.write(data[0]+"\n")
        else:
            for ident in identskeys:
                cur.execute('SELECT title from titles WHERE ident=?', (str(ident),))
                data=cur.fetchone()
                if not data==None:
                    if contlang==1: restrictedIdentsKeys.append(ident)
                    todownload.append(data[0])
                    article_list_file.write(data[0]+"\n")
        article_list_file.close() 
    
    contlang=0
    for lang in langs:

        lang_name, lang_code = get_language(lang)

        contlang+=1
        article_list="articlelist-"+lang_code+".txt"
        article_list_path = os.path.join(outdir, article_list)
        usertitles=[]
        entrada=open(article_list_path,"r",encoding="utf-8")
        for linia in entrada:
            linia=linia.rstrip()
            if linia.startswith(("File:", "Wikipedia:", "thumb")): # remove images (File:...) and Wikipedia: pages from usertitles, having a more accurate total number of pages
                continue
            usertitles.append(linia)
        entrada.close()

        usertitles_set = set(usertitles) # transforming list into a set for faster lookup, this counts pages that redirect

        print(f"\nProcessing articles in {lang_name}")

        pagesdir= f"pages-{lang_code}"
        pagesdirpath = os.path.join(outdir, pagesdir) # change to use Path library!

        processed_articles_set = set()
        processed_articles_file = f'processed-articles-{lang_code}.temp'
        processed_articles_path = outdir / processed_articles_file

        if not processed_articles_path.exists():
            print(f"processed-articles-{lang_code}.temp file created\n")
            processed_articles_path.touch()

        else: # if it exists open it, read the titles and add them to the set that it's getting checked later on
            print("Processed articles file found")
            with open(processed_articles_path, "r", encoding='utf-8') as f:
                for line in f:
                    processed_articles_set.add(line.strip())
            print(f"Number of processed articles so far: {len(processed_articles_set)}\n")

        if not os.path.exists(pagesdirpath):
            os.makedirs(pagesdirpath) 
            
        dump_path = dumpL1 if contlang == 1 else dumpL2
        redirect_titles = set()
        total = 0

        print(f"Articles to process: {len(usertitles_set)}")
        with bz2.open(dump_path, 'rb') as f:

            dump = mwxml.Dump.from_file(f)

            pbar = tqdm(dump, total=len(usertitles_set))
            for page in pbar:
                if page.redirect: # skip redirects
                    if page.title in usertitles_set:
                        redirect_titles.add(page.title)

                else: # if its not a redirect
                    if page.title in processed_articles_set:
                        continue

                    if page.title in usertitles_set: # using set for faster lookup
                        # pages_checked_counter += 1
                        pbar.set_description(f"({total}/{len(usertitles_set)}) Processing article {page.title}")

                        for revision in page:
                            text = extract_text_from_wikitext(revision.text)

                            clean_title = re.sub(r'[/\\:*?"<>|]', '_', page.title) # handle unwanted symbols that mess with the path, specially /
                            filename = clean_title.replace(" ", "_") + ".txt"  

                            full_path = os.path.join(pagesdirpath, filename)
                            try:
                                sortida=open(full_path,"w",encoding="utf-8")
                                sortida.write(page.title+"\n")
                                linies=text.split("\n")
                                for linia in linies:
                                    linia=linia.strip()
                                    
                                    if not linia.startswith(category_namespaces[lang_code]) and not linia.startswith("|") and not linia.startswith("<") and not linia.startswith("!") and not linia.startswith("{")and len(linia)>0:
                                        sortida.write(linia+"\n")
                                sortida.close()

                                processed_articles_set.add(page.title)
                                with open(processed_articles_path, "a", encoding='utf-8') as log_file: # adding titles to processed articles file and set
                                    log_file.write("\n" + page.title)
                                
                                total = len(processed_articles_set) + len(redirect_titles)
                                if total >= len(usertitles_set):
                                    break
        
                            except:
                                print("ERROR:",sys.exc_info())
                                print(f"Category namespace for {lang_name} might be missing.")

            # fix of the previous check
            if total >= len(usertitles_set):
                print(f"\nAll articles ({total}) in {lang_name} processed!")
                processed_articles_path.unlink()
                print("-" * 60)
                print(f"\nPages saved: {len(processed_articles_set)}")
                print(f"Pages skipped (redirects): {len(redirect_titles)}")

            else: # bug check
                print(f"\nOnly found {total}/{len(usertitles_set)} articles.")
                
                # missing_titles = usertitles_set - processed_articles_set - redirect_titles
                # print(f"\nCould not find {len(missing_titles)} titles in the dump")
                
                # for title in list(missing_titles)[:20]:
                #     print(f"{title}"
            
            print("-" * 60)