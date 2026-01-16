# Slime
一个非常简单的支持ai对话的桌宠。

首先是人话：闲的没事为了学习Vibe Coding写了个这玩意，也算终于用上了几年前画的都快堆灰的史莱姆娘行走图了。
然后是gemini的话：

# 🤖 AI Desktop Pet (AI 智能小桌宠)

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![PyQt6](https://img.shields.io/badge/GUI-PyQt6-green)
![License](https://img.shields.io/badge/License-MIT-orange)

一个运行在 Windows 桌面上的智能 AI 伴侣。它不仅会在你的屏幕上自由漫步，更是你工作学习时的贴心助手，随时陪你聊天解闷！

> **项目状态**: ✅ 开发完成 | 🚀 已发布

## ✨ 核心功能

- **🎨 灵动交互**
  - **透明无边框**: 完美融入桌面环境，不遮挡视线。
  - **随机漫步**: 像真实宠物一样在屏幕上自由走动、发呆。
  - **鼠标互动**: 支持拖拽玩耍，点击即可唤醒对话。
  - **智能朝向**: 点击时会自动停下脚步，转过身来注视着你（面朝屏幕前方）。

- **🧠 强大 AI 大脑**
  - **多模型支持**: 兼容 OpenAI 格式 API，支持 GPT-3.5/4, DeepSeek, Claude (via OneAPI) 等多种模型。
  - **智能对话**: 支持流式思考（显示 "..."），回复内容支持长文本自动垂直滚动。
  - **上下文记忆**: 拥有短时记忆，能记住你们之前的聊天内容。
  - **角色扮演**: 支持自定义角色提示词（System Prompt），你可以把它设定为傲娇猫娘、高冷管家或者任何你喜欢的角色！

- **🛠️ 高度可定制**
  - **专属命名**: 首次启动即可取名，提示词中支持 `{char}` 占位符自动注入名字。
  - **历史回溯**: 内置历史记录查看器（🕒 图标），随时翻看过往的温馨对话。
  - **托盘管理**: 右键系统托盘图标即可快速配置 API、更换模型或清除记忆。

## 📦 安装与运行

### 1. 环境准备
确保你的电脑已安装 Python 3.10 或更高版本。

### 2. 安装依赖
在项目根目录下运行终端命令：

```bash
pip install -r requirements.txt
```
*(如果没有 requirements.txt，可以直接通过 pip install PyQt6 requests 安装)*

### 3. 启动桌宠
```bash
python main.py
```

## ⚙️ 配置说明

1.  **启动程序**后，右键点击任务栏右下角的托盘小图标。
2.  选择 **"配置 AI"**。
3.  填入你的 API 信息：
    *   **API Endpoint**: 例如 `https://api.openai.com/v1/chat/completions` (支持自动修正基础 URL)
    *   **API Key**: 你的密钥 `sk-xxxxxx`
    *   **模型选择**: 手动输入或点击“拉取模型列表”自动获取。
4.  点击保存，开始对话吧！

## 📂 项目结构

```
ai-desktop-pet/
├── assets/
│   └── sprite.png       # 角色行走图素材 (96x128, 3x4 布局)
├── config.json          # 配置文件 (自动生成，含 API 加密信息)
├── history.json         # 对话历史记录 (自动生成)
├── main.py              # 主程序入口
└── README.md            # 项目说明文档
```

## 🛡️ 安全与隐私
*   所有 API Key 仅保存在本地 `config.json` 中，不会上传至任何第三方服务器。
*   对话历史仅存储在本地 `history.json`。

## 🤝 贡献
欢迎提交 Issue 或 Pull Request 来改进这个小家伙！无论是增加新的动作、优化 AI 逻辑还是添加更有趣的功能，都非常欢迎。

---
*Made with ❤️ by Antigravity*


---
突然被问是不是可以换Niko的行走图，忘了说了行走图只要是96*128的png格式图片应该都适配，有哪里不对按照我提供的史莱姆娘行走图微调就好。
就这样随便玩随便换都可以，反正本人概不负责（什）。后续我可能会更新新功能（吗？）
