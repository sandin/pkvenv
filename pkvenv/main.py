import os
import requests
import argparse
import subprocess
import shutil
import json
from pathlib import Path
from . import __version__

ROOT_DIR = os.path.abspath(os.path.dirname(__file__))
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


def get_embed_python_url(py_version_str, os_arch = "amd64"):
    if py_version_str == "3.7.2":
        filename = f"python-3.7.2.post1-embed-{os_arch}.zip"
    elif py_version_str == "3.7.3":
        filename = f"python-3.7.3rc1-embed-{os_arch}.zip"
    elif py_version_str == "3.7.4":
        filename = f"python-3.7.4rc2-embed-{os_arch}.zip"
    # TODO:
    else:
        filename = f"python-{py_version_str}-embed-{os_arch}.zip"
    url = f"https://www.python.org/ftp/python/{py_version_str}/{filename}"
    return filename, url


def fetch_embeddable_python(py_version_str, os_arch = "amd64"):
    # eg: https://www.python.org/ftp/python/3.9.2/python-3.9.2-embed-amd64.zip
    cache_dir = get_cache_dir()
    filename, url = get_embed_python_url(py_version_str, os_arch)
    cache_file = os.path.join(cache_dir, filename)
    if not os.path.exists(cache_file):
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


def get_new_requirements(venv_path, output_path, py_version):
    bin_path = os.path.join(venv_path, "Scripts")
    python_path = find_python_bin_from_path(bin_path)
    print("Found python path: ", python_path)
    if not os.path.exists(python_path):
        raise ValueError("%s is not exists" % python_path)
    output = subprocess.check_output([python_path, "-m", "pip", "freeze"], cwd=bin_path)
    new_requirements_file = os.path.join(output_path, "requirements.txt")
    with open(new_requirements_file, "w") as f:
        for line in output.decode("utf-8").split("\n"):
            line = line.strip()
            if "pkvenv" in line:
                continue  # ?????????pkvenv??????
            if line.startswith("-e "):
                line = line[3:]  # -e?????????????????????editable??????
            f.write(line)
            f.write(os.linesep)
    return new_requirements_file


def setup_python(python_zip_file, requirements_file, output_path):
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

    output = subprocess.check_output([python_path, "-m", "pip", "install", "-r", requirements_file], cwd=bin_path)
    print("install requirements_file", output)


def copy_files(files, output_path, name, is_gui):
    # copy include file to pkvenv_package model dir
    pkvenv_package_path = os.path.join(output_path, "Python", "Lib", "site-packages", "pkvenv_package")
    if os.path.exists(pkvenv_package_path):
        shutil.rmtree(pkvenv_package_path, ignore_errors=True)
    os.makedirs(pkvenv_package_path, exist_ok=True)

    if not os.path.exists(pkvenv_package_path):
        os.mkdir(pkvenv_package_path)

    for file in files:
        if os.path.isfile(file):
            shutil.copy(file, pkvenv_package_path)
        elif os.path.isdir(file):
            shutil.copytree(file, os.path.join(pkvenv_package_path, os.path.basename(file)))
        else:
            print("[Warning] %s file is not a file or dir" % file)

    # copy .exe to root directory
    if is_gui:
        shutil.copy(os.path.join(ROOT_DIR, "launch_gui.exe.py"), os.path.join(output_path, "%s.exe" % name))
    else:
        shutil.copy(os.path.join(ROOT_DIR, "launch.exe.py"), os.path.join(output_path, "%s.exe" % name))


def zip_files(output_path, name):
    build_path = os.path.dirname(output_path)
    shutil.make_archive(os.path.join(build_path, name), "zip", output_path)


def gen_launch_file(output_path, args):
    # ?????? pkvenv_main model, ????????????pkvenv_main model????????? pkvenv_package.
    pkvenv_main_path = os.path.join(output_path, "Python", "Lib", "site-packages", "pkvenv_main")
    if os.path.exists(pkvenv_main_path):
        shutil.rmtree(pkvenv_main_path, ignore_errors=True)
    os.makedirs(pkvenv_main_path, exist_ok=True)

    tmp = args.split(":")
    module_names = tmp[0].split(".")
    function_name = tmp[1]

    main_file = os.path.join(pkvenv_main_path, "__main__.py")
    package_name = "." + ".".join(module_names[0:-1]) if module_names[0:-1] else ""
    with open(main_file, "w") as f:
        f.write("from pkvenv_package%s import %s%s" % (package_name, module_names[-1], os.linesep))
        f.write("%s.%s()%s" % (module_names[-1], function_name, os.linesep))

    init_file = os.path.join(pkvenv_main_path, "__init__.py")
    with open(init_file, "w") as f:
        pass



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
    args = configs["entry_point"] if "entry_point" in configs else None
    venv = configs["venv"] if "venv" in configs else None
    include = configs["include"] if "include" in configs else None
    gui = bool(configs["gui"]) if "gui" in configs else False
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
    print("Found venv configs:", venv_configs, venv_path)
    py_version = get_py_version_from_str(venv_configs['version'])
    new_requirements_file = get_new_requirements(venv_path, output_path, py_version)
    print("Found new requirements file:", new_requirements_file)

    embed_python_zip_file = fetch_embeddable_python(venv_configs['version'])
    print("Fetch embed python:", embed_python_zip_file)
    setup_python(embed_python_zip_file, new_requirements_file, output_path)

    copy_files(include_files, output_path, name, gui)
    gen_launch_file(output_path, args)
    zip_files(output_path, name)





if __name__ == "__main__":
    main()
