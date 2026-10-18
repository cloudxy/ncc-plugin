# 公开合成拆书样例

本目录为本项目自写的极短文本，不包含真实书稿。multi-volume.txt 覆盖序章、多卷重号、缩进回声、同号分章、原号跳号与短章警告。预期 seq=1..5，no=[0,1,1,3,1]，两个“雨夜”有不同 part；仅标题回声被忽略，正文有证据可定位。

完整最小章对象、错类型/错版本/错 hash/错包、坏 JSON、条目隔离、稀疏上下文、状态冲突、场次、源变更和写入中断样例由 test_deconstruction.py 在临时目录构造。绝不读取 novels、books 或个人原文，不调用模型，不联网。

作者可运行：

```bash
python3 -m unittest scripts.tests.test_deconstruction
```

从仓库运行时推荐统一发现入口，避免依赖导入路径：

```bash
python3 -m unittest discover -s scripts/tests -t scripts -p 'test_deconstruction.py'
```

本轮仅交付用例；尚未执行，不称这些预期已经通过。
