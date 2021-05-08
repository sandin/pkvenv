# PKVENV

将Python Venv环境整体打包成EXE。

# Install

```
# pip install pkvenv
```

# Usage


```
pkvenv project_dir
```

其中 project_dir 为项目根目录，该目录下必须存在 `pkvenv.json` 配置文件，该配置文件提供了打包EXE所需的所有参数。

pkvenv.json

```
{
    "name": "Application Name",
    "entry_point": "app:main",
    "venv": "./venv",
    "gui": false,
    "include" : [
        "app.py",
        "index.html",
        "res"
    ]
}

```

* name: 应用名称
* entry_point: 入口函数（格式：module_name:function_name, 例如 `app:main`, 则会启动 `app.py` 里面的 `main()` 函数 ) 
* venv: Python Venv路径，打包脚本会去读取该Venv环境中的配置文件，将该Venv使用的Python版本以及里面所有已经安装的pip依赖打包到EXE包内。
* include: 需要打包到包内的文件列表（包括python源码和资源文件等, 支持文件名或者目录名）
* gui: 是否为GUI程序，非GUI程序用 `python.exe` 启动，GUI程序用 `pythonw.exe` 启动，默认为false

打包后会在 `${project_dir}/build` 目录下生成一个 `${Application Name}.zip` 的绿色安装包，其中 `${Application Name}.exe` 为启动程序。

启动该程序会等于执行打入包内的 `Python\pythonw.exe app-script.py` 来拉起python脚本。
