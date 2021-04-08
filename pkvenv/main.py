import os
import requests
import argparse
import subprocess
import shutil
import json
from pathlib import Path
from . import __version__

CONFIG_FILE_NAME = "pkvenv.json"

def get_cache_dir():
    cache_dir = os.path.join(str(Path.home()), ".pkevnv")
    if not os.path.exists(cache_dir):
        os.mkdir(cache_dir)
    elif os.path.islink(cache_dir) or os.path.isfile(cache_dir):
        raise ValueError("Can not create cache dir!")
    return cache_dir


def download_file(url, output):
    req = requests.get(url, {'user-agent': "pkvenv/" + __version__}, stream=True)
    req.raise_for_status()
    with open(output, "wb") as f:
        for chunk in req.iter_content(chunk_size=1024):
            if chunk:
                f.write(chunk)


def fetch_embeddable_python(py_version_str, os_arch = "amd64"):
    # eg: https://www.python.org/ftp/python/3.9.2/python-3.9.2-embed-amd64.zip
    cache_dir = get_cache_dir()
    filename = f"python-{py_version_str}-embed-{os_arch}.zip"
    cache_file = os.path.join(cache_dir, filename)
    if not os.path.exists(cache_file):
        url = f"https://www.python.org/ftp/python/{py_version_str}/{filename}"
        print("Downloading %s" % url)
        download_file(url, cache_file)
        print("Download finish %s" % cache_file)
    return cache_file


def parse_venv_configs(venv_path):
    configs = {}
    cfg_file = os.path.join(venv_path, "pyvenv.cfg")
    if not os.path.exists(cfg_file):
        raise ValueError("%s is not exists" % cfg_file)
    with open(cfg_file, "r") as f:
        for line in f.readlines():
            if line.index("=") != -1:
                tmp = line.split("=")
                if len(tmp) == 2:
                    configs[tmp[0].strip()] = tmp[1].strip()
    return configs


def parse_requirements(txt):
    requirements = []
    for line in txt.split("\n"):
        line = line.strip()
        if "==" in line:
            tmp = line.split("==")
            if len(tmp) == 2:
                requirements.append(tmp) # [name, version]
    return requirements


def write_requirements_file(requirements, output_file):
    with open(output_file, "w") as f:
        for item in requirements:
            f.write(item[0])
            f.write("==")
            f.write(item[1])
            f.write(os.linesep)


def get_py_version_from_str(py_version_str):
    if "." in py_version_str:
        versions = py_version_str.split(".")
        if len(versions) == 3:
            return versions
        elif len(versions) == 2:
            return versions + [0]
        elif len(versions) == 1:
            return versions + [0, 0]
    raise ValueError("invalid python version %s" % py_version_str)


def find_python_bin_from_path(path):
    python_path = None
    if os.name != "nt":
        for suffix in ('python', 'python3'): # TODO: format: python3.7, python3.8
            path = os.path.join(path, suffix)
            if os.path.exists(path):
                python_path = path
                break
    else:
        python_path = os.path.join(path, "python.exe")
    return python_path


def parse_venv_requirements(venv_path, py_version):
    bin_path = os.path.join(venv_path, "Scripts")
    python_path = find_python_bin_from_path(bin_path)
    if not os.path.exists(python_path):
        raise ValueError("%s is not exists" % python_path)
    output = subprocess.check_output([python_path, "-m", "pip", "freeze"], cwd=bin_path)
    return parse_requirements(output.decode("utf-8"))



def setup_python(python_zip_file, requirements, output_path):
    bin_path = os.path.join(output_path, "Python")
    shutil.unpack_archive(python_zip_file, bin_path)
    found_python_path_file = False
    for filename in os.listdir(bin_path):
        if filename.startswith("python") and filename.endswith("._pth"): # python37._pth
            found_python_path_file = True
            with open(os.path.join(bin_path, filename), "a") as f:
                #f.write("..\\pkgs")
                f.write("..")
                f.write(os.linesep)
                f.write("import site")
                f.write(os.linesep)
                break
    if not found_python_path_file:
        raise ValueError("Can not found python._pth file")

    cache_dir = get_cache_dir()
    get_pip_file = os.path.join(cache_dir, "get-pip.py")
    if not os.path.exists(get_pip_file):
        get_pip_url = "https://bootstrap.pypa.io/get-pip.py"
        download_file(get_pip_url, get_pip_file)

    python_path = find_python_bin_from_path(bin_path)
    if not os.path.exists(python_path):
        raise ValueError("python bin file(%s) is not exists" % python_path)

    output = subprocess.check_output([python_path, get_pip_file], cwd=bin_path)
    print("get_pip", output)

    requirements_file = os.path.join(bin_path, "requirements.txt")
    write_requirements_file(requirements, requirements_file)
    output = subprocess.check_output([python_path, "-m", "pip", "install", "-r", requirements_file], cwd=bin_path)
    print("install requirements_file", output)


def copy_files(files, output_path):
    #pkgs_path = os.path.join(output_path, "pkgs")
    pkgs_path = os.path.join(output_path, ".")
    if not os.path.exists(pkgs_path):
        os.mkdir(pkgs_path)

    for file in files:
        if os.path.isfile(file):
            shutil.copy(file, pkgs_path)
        elif os.path.isdir(file):
            shutil.copytree(file, pkgs_path)
        else:
            print("[Warning] %s file is not a file or dir" % file)


def gen_launch_file(output_path, name, args):
    launch_file = os.path.join(output_path, "%s.bat" % name)
    with open(launch_file, "w") as f:
        f.write("Python\python.exe " + args)

def main():
    print("pkvenv %s" % __version__)
    argparser = argparse.ArgumentParser()
    argparser.add_argument("project_dir", help="project dir")
    arguments = argparser.parse_args()

    project_dir = os.path.abspath(arguments.project_dir)
    if not os.path.exists(project_dir) or not os.path.isdir(project_dir):
        print("Error: project directory(%s) is not exists or not a directory!" % project_dir)
        exit(-1)

    configs_file = os.path.join(project_dir, CONFIG_FILE_NAME)
    if not os.path.exists(configs_file):
        print("Error: config file(%s) is not exists!" % configs_file)
        exit(-1)

    configs = None
    with open(configs_file, "r") as f:
        try:
            configs = json.load(f)
        except:
            pass
    if not configs:
        print("Error: can not parse config file!")
        exit(-1)

    name = configs["name"] if "name" in configs else None
    args = configs["args"] if "args" in configs else None
    venv = configs["venv"] if "venv" in configs else None
    include = configs["include"] if "include" in configs else None
    if name is None:
        print("Error: `name` is missing in config file!")
        exit(-1)
    if args is None:
        print("Error: `args` is missing in config file!")
        exit(-1)
    if venv is None:
        print("Error: `venv` is missing in config file!")
        exit(-1)
    if include is None:
        print("Error: `include` is missing in config file!")
        exit(-1)

    venv_path = os.path.abspath(os.path.join(project_dir, venv))
    include_files = []
    for item in include:
        include_files.append(os.path.abspath(os.path.join(project_dir, item))) # TODO: dir

    output_path = os.path.join(project_dir, "build", "pkvenv")
    if os.path.exists(output_path):
        shutil.rmtree(output_path, ignore_errors=True)
    os.makedirs(output_path, exist_ok=True)

    venv_configs = parse_venv_configs(venv_path)
    if "version" not in venv_configs:
        print("Error: Can not find python version is venv config file!")
        exit(-1)
    print("Found venv configs:", venv_configs)
    py_version = get_py_version_from_str(venv_configs['version'])
    venv_requirements = parse_venv_requirements(venv_path, py_version)
    print("Found venv requirements:", venv_requirements)

    embed_python_zip_file = fetch_embeddable_python(venv_configs['version'])
    print("Fetch embed python:", embed_python_zip_file)
    setup_python(embed_python_zip_file, venv_requirements, output_path)

    copy_files(include_files, output_path)
    gen_launch_file(output_path, name, args)





if __name__ == "__main__":
    main()