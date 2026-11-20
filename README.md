# Sublime CPH

一个面向 Sublime Text 4 的 C++ 竞赛编程辅助工具，兼容 Competitive Companion。

## 功能

- 监听 `127.0.0.1:10045` 接收题目
- 保存全部测试样例到 `~/Code/cph/<题目名>/`
- 使用 `~/Code/template.cpp` 创建题目代码内容
- 生成与 CP Editor 一致的题目信息头注释（不包含 Powered by 行）
- 按 `~/Code/template.js` 的规则生成题目文件名（例如 `CF123A Two Sum.cpp`）
- `Alt+Shift+F` 使用项目 `.clang-format` 格式化当前 C++ 文件
- `F9` 编译
- `F10` 编译并运行第一组样例
- `F12` 编译并测试全部样例
- 样例面板可预览、编辑和测试单组样例，也可导入成对的输入和答案

## 安装

```bash
./scripts/install.sh
```

重启 Sublime Text 后插件会自动启动监听器；也可以从顶部菜单 `Competitive Helper > Start Listener` 手动启动。
然后将 Competitive Companion 的 Custom Port 设置为 `10045`，在题目页面点击扩展按钮即可。

格式化命令默认使用系统中的 `clang-format`，并从当前源文件目录向上查找 `.clang-format`。可在
`CompetitiveHelper.sublime-settings` 中通过 `clang_format_program` 修改可执行文件名或路径。

## 样例面板

打开已保存的 C++ 文件，选择 **Competitive Helper → 样例面板**，或在命令面板运行 **Competitive Helper: Samples**。

- 可以直接预览输入、预期输出和程序输出。点击标题可打开完整文件，编辑输入和答案后保存即可。
- **新建样例**会创建空的输入与答案文件。**导入文件对**先选输入、再选答案，单组可以使用不同文件名，批量导入按同名匹配。答案可选 `.ans`、`.out` 或 `.txt`。
- 新增样例使用 `custom_序号.in` 和 `custom_序号.ans`，测试生成同名 `.out`。跑单组或全部后会显示判定和用时，文件太大时只显示开头。

## 文件读写

测试默认使用 stdin/stdout。运行器会检查编译器实际启用的代码，识别带固定文件名的 `freopen` 和本仓库模板中的 `Judge_File`、`Local_File`。启用文件读写时，每组样例在独立的临时目录运行，运行器准备输入文件并读取程序生成的输出文件。

动态计算文件名或使用 `ifstream` / `ofstream` 时，可以在该题样例目录创建 `io.json` 指定名称：

```json
{
  "input": "task.in",
  "output": "task.out"
}
```

只重定向一侧时可以省略另一侧，或者写成 `null`。如果要强制按 stdin/stdout 测试，使用空对象 `{}`。

## 测试

```bash
python3 -m unittest discover -s tests -v
```
