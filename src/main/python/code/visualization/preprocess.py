import zipfile

def unzip_file(zip_file_path, output_file_path):
    with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
        zip_ref.extractall(output_file_path.parent)
    return output_file_path

def run(data_dir):
    print(f"Preprocessing data in {data_dir}...", flush=True)
    log_dir = data_dir / "logs"
    lock_file = log_dir / ".lock"
    if lock_file.exists():
        print(f"Lock file {lock_file} exists. Skipping preprocessing.", flush=True)
        return
    
    lock_file.touch()  
    dirs = [d for d in log_dir.iterdir() if d.is_dir()]
    all_files = []
    file_prefix = set({})
    
    for d in dirs:
        files = list(d.iterdir())
        all_files.extend(files)
        file_prefix.update((f.name.split("-")[0], f.name.split(".")[1]) for f in files)
    
    for prefix, ext in file_prefix:
        matching_files = [f for f in all_files if f.name.split("-")[0] == prefix and f.name.split(".")[1] == ext]
        if len(matching_files) > 0:
            print(f"Found {len(matching_files)} files with prefix '{prefix}' and extension '{ext}':")
            # Concatenate files
            output_file = log_dir / f"{prefix}.{ext}"
            # rename the current file in the output
            if output_file.exists():
                output_file.rename(log_dir / f"{prefix}_old.{ext}")
                matching_files.append(log_dir / f"{prefix}_old.{ext}")
            with open(output_file, "wb") as wfd:
                for f in matching_files:
                    if f.name.endswith(".zip"):
                        f_unzipped = f.name.split(".zip")[0]
                        f_unzipped_path = log_dir / f_unzipped
                        f = unzip_file(f, f_unzipped_path)
                        with open(f, "rb") as fd:
                            wfd.write(fd.read())
                        f_unzipped_path.unlink()
                    else:
                        with open(f, "rb") as fd:
                            wfd.write(fd.read())

    print("Preprocessing complete.", flush=True)