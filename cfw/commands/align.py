"""
This file contains some utilities functions used to find parallel sentences
in two monolingual corpora.

Code in this file has been adapted from the LASER repository:
https://github.com/facebookresearch/LASER
"""

def file_open(filepath):
    import gzip
    import lzma
    from pathlib import Path
    if Path(filepath).name.endswith('.gz'):
        return gzip.open(filepath, 'rt', encoding='utf-8')
    elif Path(filepath).name.endswith('xz'):
        return lzma.open(filepath, 'rt', encoding='utf-8')
    else:
        return open(filepath, 'r', encoding='utf-8')

def score_candidates_vectorized(x_f16, y_f16, candidate_inds, fwd_mean, bwd_mean, scoring_chunk_size):
    import numpy as np
    """
    Vectorized margin-based scoring running in safe row chunks.
    """
    print("Computing vectorized margin scores", flush=True)
    num_queries = x_f16.shape[0]
    k = candidate_inds.shape[1]
    scores = np.zeros((num_queries, k), dtype=np.float32)
     
    for start in range(0, num_queries, scoring_chunk_size):
        end = min(start + scoring_chunk_size, num_queries)
        
        batch_x = x_f16[start:end].astype('float32') 
        batch_inds = candidate_inds[start:end]
        batch_y = y_f16[batch_inds].astype('float32') 
        
        dots = np.einsum('id,ikd->ik', batch_x, batch_y)
        
        batch_fwd_mean = fwd_mean[start:end, np.newaxis]
        batch_bwd_mean = bwd_mean[batch_inds]
        
        scores[start:end] = dots / ((batch_fwd_mean + batch_bwd_mean) / 2)
        
        del batch_x, batch_y, dots
    return scores

def align_corpora(args):
    import gc
    import tqdm
    import faiss
    import torch
    import numpy as np
    from pathlib import Path
    from sentence_transformers import SentenceTransformer
    from ..utils.get_language import get_language

    print("\nRunning align command", flush=True)

    device = args.device.lower()
    if device == 'gpu' and not torch.cuda.is_available():
        print("GPU requested but not found. Using CPU.", flush=True)
        device = 'cpu'

    indir_source = Path(args.indir)
    input_directories = [indir_source]

    if args.optional_indir:
        input_directories.append(Path(args.optional_indir))

    if len(input_directories) == 1:
        folder_name = input_directories[0]
        folder_name = folder_name.stem.split("-")
        source_lang_code = folder_name[-2]
        target_lang_code = folder_name[-1]
    elif len(input_directories) == 2:
        source_folder_name = input_directories[0]
        target_folder_name = input_directories[1]
        source_lang_code = source_folder_name.stem.split("-")[-1]
        target_lang_code = target_folder_name.stem.split("-")[-1]
        
    unique_segments_files = []
    for indir in input_directories:
        for file in indir.iterdir():
            if file.is_file() and file.stem.startswith("unique-segments") and file.stem.endswith(source_lang_code):
                unique_segments_files.append(file)
                source_file = file
            if file.is_file() and file.stem.startswith("unique-segments") and file.stem.endswith(target_lang_code):
                unique_segments_files.append(file)
                target_file = file
    print("")
    for file in unique_segments_files:
        print(f"Unique segments file {file.name} found", flush=True)

    source_lang_name, source_lang_code = get_language(source_lang_code)
    target_lang_name, target_lang_code = get_language(target_lang_code)
    print(f"\nAligning {source_lang_name} and {target_lang_name} segments\n", flush=True)

    outdir = args.outdir
    parallel_corpora_folder = indir_source.parent.parent / "parallel"

    if not parallel_corpora_folder.exists():
        parallel_corpora_folder.mkdir(parents=True, exist_ok=True)

    if not outdir:
        if len(input_directories) > 1: # if we are aligning separate corpora in different folders
            outdir = parallel_corpora_folder / f"aligned-{source_lang_code}-{target_lang_code}/"
            if not outdir.exists():
                outdir.mkdir(parents=True, exist_ok=True)
        else: # else just save the file in the same input directory
            outdir = indir

    gpus_num = torch.cuda.device_count()
    devices_num = [f"cuda:{i}" for i in range(gpus_num)]
    print(f"Visible GPUs: {devices_num}", flush=True)
    
    mode = args.mode
    print(f"\nApplying '{mode.upper()}' performance mode", flush=True)

    if mode == 'fast':
        # high end hardware (80gb vram, 128gb ram)
        preset_batch = 512 # lower?
        preset_chunk = 50000
        preset_search = 4096
        scoring_chunk_size = 1000000  
    elif mode == 'balanced':
        # pro/medium hardware (24gb vram, 64gb ram)
        preset_batch = 256
        preset_chunk = 25000
        preset_search = 2048
        scoring_chunk_size = 500000
    else: # 'safe'
        # standard consumer hware (8gb vram, 16gb ram)
        preset_batch = 64
        preset_chunk = 10000
        preset_search = 1024
        scoring_chunk_size = 100000 

    # if user overrides
    batch_size = preset_batch
    chunk_size = preset_chunk
    search_chunk_size = preset_search

    min_sent_len = 10
    max_sent_len = 200

    knn_neighbors = 4
    min_threshold = 1

    print(f"Reading source ({source_lang_name}) file", flush=True)
    source_sentences = set()
    with file_open(source_file) as fIn:
        for line in tqdm.tqdm(fIn):
            line = line.strip()
            if min_sent_len <= len(line) <= max_sent_len:
                source_sentences.add(line)

    print(f"Reading target ({target_lang_name}) file", flush=True)
    target_sentences = set()
    with file_open(target_file) as fIn:
        for line in tqdm.tqdm(fIn):
            line = line.strip()
            if min_sent_len <= len(line) <= max_sent_len:
                target_sentences.add(line)

    source_sentences = sorted(list(source_sentences))
    target_sentences = sorted(list(target_sentences))
    
    print(f"Source Sentences: {len(source_sentences)} | Target Sentences: {len(target_sentences)}", flush=True)

    src_cache = indir / f"embeddings-{source_lang_code}.npy"
    trg_cache = indir / f"embeddings-{target_lang_code}.npy"

    model = SentenceTransformer('LaBSE')
        
    if gpus_num > 1:
        print(f"\nUsing multiprocessing pool across {gpus_num} GPUs", flush=True)
        pool = model.start_multi_process_pool(target_devices=devices_num)
        encode_kwargs = {'pool': pool}
    else:
        encode_device = devices_num[0] if gpus_num == 1 else 'cpu'
        print(f"\nUsing single device ({encode_device})", flush=True)
        pool = None
        encode_kwargs = {'device': encode_device}

    try:
        print("Encoding source sentences", flush=True)
        source_embeddings = model.encode(
            source_sentences, 
            show_progress_bar=True, 
            chunk_size=chunk_size, 
            batch_size=batch_size, 
            convert_to_numpy=True, 
            normalize_embeddings=True,
            **encode_kwargs  # pool or device
        )
        source_embeddings = source_embeddings.astype(np.float16)
        np.save(src_cache, source_embeddings)
        
        del source_embeddings
        gc.collect()

        print("Encoding target sentences", flush=True)
        target_embeddings = model.encode(
            target_sentences, 
            show_progress_bar=True, 
            chunk_size=chunk_size, 
            batch_size=batch_size, 
            convert_to_numpy=True, 
            normalize_embeddings=True,
            **encode_kwargs # pool or device
        )
        target_embeddings = target_embeddings.astype(np.float16)
        np.save(trg_cache, target_embeddings)
        
        del target_embeddings
        gc.collect()
        
    finally:
        if pool is not None:
            model.stop_multi_process_pool(pool=pool)

    co = faiss.GpuMultipleClonerOptions()
    co.shard = True
    co.useFloat16 = True
    
    search_chunk_size = 4096

    # first pass, source to target
    print(f"\nLoading {source_lang_name} vectors into GPU Index", flush=True)
    y_f16 = np.load(trg_cache)
    y_f32 = y_f16.astype('float32')
    del y_f16
    gc.collect()

    cpu_index_y = faiss.IndexFlatIP(y_f32.shape[1])
    gpu_index_y = faiss.index_cpu_to_all_gpus(cpu_index_y, co)
    gpu_index_y.add(y_f32)
    del y_f32
    gc.collect()

    print("Searching Target Index in optimized chunks", flush=True)
    x_f16 = np.load(src_cache)
    x2y_sim = np.zeros((x_f16.shape[0], knn_neighbors), dtype=np.float32)
    x2y_ind = np.zeros((x_f16.shape[0], knn_neighbors), dtype=np.int64)

    # prog bar
    for start in tqdm.tqdm(range(0, x_f16.shape[0], search_chunk_size), desc="Target Search Progress"):
        end = min(start + search_chunk_size, x_f16.shape[0])
        chunk_x_f32 = x_f16[start:end].astype('float32')
        chunk_sim, chunk_ind = gpu_index_y.search(chunk_x_f32, knn_neighbors)
        x2y_sim[start:end] = chunk_sim
        x2y_ind[start:end] = chunk_ind
        del chunk_x_f32

    del gpu_index_y
    gc.collect() 

    # pass b, target to source (xf32)
    print(f"\nLoading {target_lang_name} vectors into GPU Index", flush=True)
    x_f32 = x_f16.astype('float32')
    cpu_index_x = faiss.IndexFlatIP(x_f32.shape[1])
    gpu_index_x = faiss.index_cpu_to_all_gpus(cpu_index_x, co)
    gpu_index_x.add(x_f32)
    del x_f32
    gc.collect()

    print("Searching Source Index in optimized chunks", flush=True)
    y_f16 = np.load(trg_cache)
    y2x_sim = np.zeros((y_f16.shape[0], knn_neighbors), dtype=np.float32)
    y2x_ind = np.zeros((y_f16.shape[0], knn_neighbors), dtype=np.int64)

    for start in tqdm.tqdm(range(0, y_f16.shape[0], search_chunk_size), desc="Source Search Progress"):
        end = min(start + search_chunk_size, y_f16.shape[0])
        chunk_y_f32 = y_f16[start:end].astype('float32')
        chunk_sim, chunk_ind = gpu_index_x.search(chunk_y_f32, knn_neighbors)
        y2x_sim[start:end] = chunk_sim
        y2x_ind[start:end] = chunk_ind
        del chunk_y_f32

    del gpu_index_x
    gc.collect()

    print("\nPreparing margin calculation arrays", flush=True)
    x2y_mean = x2y_sim.mean(axis=1)
    y2x_mean = y2x_sim.mean(axis=1)

    fwd_scores = score_candidates_vectorized(x_f16, y_f16, x2y_ind, x2y_mean, y2x_mean, scoring_chunk_size)
    bwd_scores = score_candidates_vectorized(y_f16, x_f16, y2x_ind, y2x_mean, x2y_mean, scoring_chunk_size)

    del x_f16, y_f16
    gc.collect()

    print("\nProcessing pair evaluations", flush=True)
    fwd_best = x2y_ind[np.arange(x2y_sim.shape[0]), fwd_scores.argmax(axis=1)]
    bwd_best = y2x_ind[np.arange(y2x_sim.shape[0]), bwd_scores.argmax(axis=1)]

    indices = np.stack([
        np.concatenate([np.arange(x2y_sim.shape[0]), bwd_best]), 
        np.concatenate([fwd_best, np.arange(y2x_sim.shape[0])])
    ], axis=1)
    
    scores = np.concatenate([fwd_scores.max(axis=1), bwd_scores.max(axis=1)])
    
    del fwd_scores, bwd_scores, x2y_ind, y2x_ind
    gc.collect()

    seen_src, seen_trg = set(), set()
    sentences_written = 0
    outfile = outdir / f'aligned-segments-{source_lang_code}-{target_lang_code}.txt'
    
    print(f"Writing aligned segments to: {outfile}", flush=True)
    with open(outfile, 'w', encoding='utf-8') as fOut:
        for i in np.argsort(-scores):
            src_ind, trg_ind = indices[i]
            src_ind, trg_ind = int(src_ind), int(trg_ind)

            if scores[i] < min_threshold:
                break

            if src_ind not in seen_src and trg_ind not in seen_trg:
                seen_src.add(src_ind)
                seen_trg.add(trg_ind)
                clean_src = source_sentences[src_ind].replace("\t", " ")
                clean_trg = target_sentences[trg_ind].replace("\t", " ")
                fOut.write(f"{clean_src}\t{clean_trg}\t{scores[i]:.4f}\n")
                sentences_written += 1

    print(f"\n{sentences_written} sentences successfully aligned.\nAligned segments file saved.")

    src_cache.unlink()
    trg_cache.unlink()
