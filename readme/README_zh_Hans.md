# ElysianRealmAssistant

ElysianRealmAssistant 是一个用于 崩坏3 往世乐土 查询的 LangBot 插件。它会根据用户消息返回当前推荐图、角色攻略图片或别名列表。

## 安装

参照详细的[插件安装说明](https://docs.langbot.app/zh/plugin/plugin-intro#安装插件)

## 使用

### `乐土推荐`指令

依照推荐度排序，支持添加序号请求

![image](https://github.com/user-attachments/assets/9c30491c-8ad7-4aed-acfe-8ef29dab8dde)

![image](https://github.com/user-attachments/assets/ea3ef8ea-ae9c-44c8-874b-117cc2707bef)

### 攻略搜索指令

![image](https://github.com/user-attachments/assets/4fea1c40-a954-4be9-baf0-6d37173dc68c)

### `乐土list`指令

可查询相关关键词的列表，支持模糊匹配，输入`乐土list`可查询全文

![image](https://github.com/user-attachments/assets/980d35a1-cf88-498a-bdae-1b88d356e894)

### 异常处理

![image](https://github.com/user-attachments/assets/96a3dc7b-9696-4fd0-bad0-fa46928a1a73)

![image](https://github.com/user-attachments/assets/90aacfd5-f46a-45b2-aa6c-28289435623c)


### 角色名部分仅匹配五个字符

![image](https://github.com/user-attachments/assets/9bc12c87-4ce0-426d-aa75-20c9b125f0ac)

## 更新日志

### v1.7.0

重构 `乐土推荐` 的 api 处理逻辑，减少对上游数据的依赖

### v1.5.0

米游社图片获取部分，不知道是不是个例，dns解析耗时过长，因此加入缓存机制；单次缓存中采用单session复用方案，加快缓存速度。

### v1.2.0

提供了以下报错的临时解决方案。此问题是偶发性的，我一开始没问题，后来突然就报错了，查了一下貌似是bot框架本身的权限问题。我测试过用插件可以下载图片，却发不出去，应该不是网络问题。
![image](https://github.com/user-attachments/assets/1e6cbd03-cb9c-4ee0-b249-7d80363cb71a)
![image](https://github.com/user-attachments/assets/978c7dd8-e5b7-4d77-810e-a371ceceed53)
