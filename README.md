# Sublime CPH

一个面向 Sublime Text 4 的 C++ 竞赛编程辅助工具，兼容 Competitive Companion。

## 功能

- 监听 `127.0.0.1:10045` 接收题目
- 保存全部测试样例到 `~/Code/cph/<题目名>/`
- 使用 `~/Code/template.cpp` 创建题目代码内容
- 按 `~/Code/template.js` 的规则生成题目文件名（例如 `CF123A Two Sum.cpp`）
- `F9` 编译
- `F10` 编译并运行第一组样例
- `F12` 编译并测试全部样例

## 安装

```bash
./scripts/install.sh
```

重启 Sublime Text 后插件会自动启动监听器；也可以从顶部菜单 `Competitive Helper > Start Listener` 手动启动。
然后将 Competitive Companion 的 Custom Port 设置为 `10045`，在题目页面点击扩展按钮即可。

## 测试

```bash
python3 -m unittest discover -s tests -v
```
