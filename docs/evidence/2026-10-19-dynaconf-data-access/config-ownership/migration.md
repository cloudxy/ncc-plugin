# 本机配置归属迁移

执行现行CLI init，将原根.env移入config/.env；仅记录布尔结果和权限，不输出配置原值或其摘要。未连接数据库。

```json
{
  "command_exit": 0,
  "old_file_removed": true,
  "new_file_present": true,
  "bytes_unchanged": true,
  "private_mode": "0o600"
}
```

CLI输出：

```text
配置文件已就绪：/Users/xuyun/Documents/ncc-workflow/config/.env；初始化或迁移不改变已有配置值。
```

独立复核后将迁移算法修正为原子排他rename；上面的本机首次移动发生于修正前，字节比较结果仍属实，不作为最终算法并发安全证明。最终算法的源/目标并发替换使用临时合成文件核验；本机仅再次执行init，返回0，私有文件字节保持、旧位置仍不存在。未为测试将真实配置迁回根目录。
