# Sublime CPH

一个面向 Sublime Text 4 的 C++ 竞赛编程辅助工具，兼容 Competitive Companion。

## 功能

- 监听 `127.0.0.1:10045` 接收题目
- 保存全部测试样例到 `~/Code/cph/<题目名>/`
- 使用 `~/Code/template.cpp` 创建题目代码
- `F9` 编译
- `F10` 编译并运行第一组样例
- `F12` 编译并测试全部样例

## 安装

```bash
./scripts/install.sh
```

重启 Sublime Text 后，在命令面板执行 `Competitive Helper: Start Listener`。
然后将 Competitive Companion 的 Custom Port 设置为 `10045`，在题目页面点击扩展按钮即可。

## 测试

```bash
python3 -m unittest discover -s tests -v
```
