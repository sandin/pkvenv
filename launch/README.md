# pkvenv launcher

# Build

GUI Application
```bash
$ cargo rustc -- --cfg gui -O -C link-args="res/resources_gui.res"
```

Non-GUI Application
```bash
$ cargo rustc -- -O -C link-args="res/resources.res"
```

