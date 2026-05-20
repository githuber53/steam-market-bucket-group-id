<<<<<<< HEAD
G18DA243004, G18BD283004, market_bucket_group_id, itemid, Gitemid 
=======
G18DA243004, G18BD283004, market_bucket_group_name, market_bucket_group_id, itemid, Gitemid 
>>>>>>> a04f59d (Update: Use market_bucket_group_name instead of market_hash_name)


# Steam Market Params

用于批量获取 Steam 市场参数：

<<<<<<< HEAD
- `name_list`: Steam 市场物品名称对象列表，包含 `count_id`、`name`、`Gitemid`、`start`、`status`
=======
- `name_list`: Steam 市场物品名称对象列表，包含 `count_id`、`name`(market_bucket_group_name)、`Gitemid`(market_bucket_group_id)、`start`、`status`
>>>>>>> a04f59d (Update: Use market_bucket_group_name instead of market_hash_name)
- `item_nameid`: listings 页面里的 `Market_LoadOrderSpread(...)` 参数
- `Gitemid`: Steam 新市场接口返回的 `asset_description.market_bucket_group_id`

支持游戏：

- CS2: `appid=730`，默认启用 Gitemid
- TF2: `appid=440`，默认不启用 Gitemid
- DOTA2: `appid=570`，默认不启用 Gitemid

## 直接运行

可以直接编辑 `new_Gitemid.py` 顶部配置后运行：

```python
GAME = "cs2"
OPERATION = "names"  # names / item_nameids / Gitemid / all
LIMIT = 10
DELAY = 1.0
PROCESSES = 1
SCAN_MODE = "resume"  # resume / full
USE_LOGIN_COOKIES = False
```

然后运行：

```powershell
python new_Gitemid.py
```

封装函数也可以直接调用：

```python
from new_Gitemid import save_Gitemid, save_item_nameids, save_name_list

save_name_list("cs2", limit=100)
save_item_nameids("cs2", limit=100, processes=2)
save_Gitemid("cs2", limit=100, processes=2)
```

## CLI 使用

```powershell
python -m steam_market_params update-names cs2
python -m steam_market_params update-item-nameids cs2
python -m steam_market_params update-Gitemid cs2
python -m steam_market_params update-all cs2
```

常用参数：

```powershell
python -m steam_market_params update-names cs2 --scan-mode resume --processes 2
python -m steam_market_params update-names cs2 --scan-mode full
python -m steam_market_params update-item-nameids cs2 --processes 2 --delay 1
python -m steam_market_params update-Gitemid cs2 --retry-attempts 3
python -m steam_market_params retry-item-nameids cs2
python -m steam_market_params retry-Gitemid cs2
```

## 登录 Cookies

默认未登录请求。需要登录态时，在项目根目录创建 `cookies.json`：

```json
{
  "steamLoginSecure": "...",
  "sessionid": "..."
}
```

然后运行时加 `--login`，或在 `new_Gitemid.py` 里设置：

```python
USE_LOGIN_COOKIES = True
```

`cookies.json` 已加入 `.gitignore`，避免误提交登录凭证。

## 输出文件

```text
data/
  cs2/
    names.json
    item_nameids.json
    Gitemid.json
```

`names.json` 示例：

```json
[
  {
    "count_id": 0,
<<<<<<< HEAD
    "name": "AK-47 | Fuel Injector (Minimal Wear)",
=======
    "name": "AK-47 | Fuel Injector",
>>>>>>> a04f59d (Update: Use market_bucket_group_name instead of market_hash_name)
    "Gitemid": "G1807208C043004",
    "start": 0,
    "status": "ok"
  }
]
```

`Gitemid.json` 示例：

```json
{
<<<<<<< HEAD
  "AK-47 | Fuel Injector (Minimal Wear)": {
=======
  "AK-47 | Fuel Injector": {
>>>>>>> a04f59d (Update: Use market_bucket_group_name instead of market_hash_name)
    "Gitemid": "G1807208C043004",
    "status": "ok",
    "source": "names",
    "location": null
  }
}
```

## 数据获取方式

`name_list` 使用新的 routeAction 接口：

```text
POST https://steamcommunity.com/market/search?appid=730&sort=1&dir=1
```

<<<<<<< HEAD
请求体包含 `appid`、`filters`、`price`、`sort`、`direction`、`start`。返回结果中提取 `strHash` 或 `asset_description.market_hash_name` 作为名称，提取 `asset_description.market_bucket_group_id` 作为 `Gitemid`。
=======
请求体包含 `appid`、`filters`、`price`、`sort`、`direction`、`start`。返回结果中提取 `market_bucket_group_name` 作为名称，提取 `asset_description.market_bucket_group_id` 作为 `Gitemid`。
>>>>>>> a04f59d (Update: Use market_bucket_group_name instead of market_hash_name)

`item_nameid` 仍使用 listings 页面：

```text
https://steamcommunity.com/market/listings/{appid}/{market_hash_name}
```

并从 HTML 中提取 `Market_LoadOrderSpread(<item_nameid>)`。

`Gitemid` 优先从 `names.json` 已保存的 `Gitemid` 字段生成。只有 names 中缺失时，才回退到旧 listings 关闭重定向的提取方式。

## 断点续扫与补抓

- `--scan-mode resume`: 根据已有 `names.json` 从上次位置继续扫描。
- `--scan-mode full` 或 `--force`: 从 A-Z 序列开头重新扫描。
- `item_nameids` 只抓 names 中存在但 `item_nameids.json` 缺失或为 `null` 的项。
- `Gitemid` 只抓 names 中存在但 `Gitemid.json` 缺失、为 `null` 或状态非 `ok` 的项。
- 429、5xx、连接错误会按指数退避重试；失败项保留，后续可用 retry 命令补抓。

## Tests

```powershell
python -m unittest discover -v
```

